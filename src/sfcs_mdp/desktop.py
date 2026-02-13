"""Desktop launcher for the DARK leaf Drone Vibe Engineering Studio.

Starts a local HTTP server serving the ``ui/`` directory and opens the
studio in a chromeless browser window (Edge or Chrome ``--app`` mode)
so it behaves like a native desktop application.

Hardware capabilities (GPU renderer, logical cores, device memory,
screen resolution) are forwarded as query parameters so the front-end
can auto-select an appropriate rendering fidelity level.
"""

from __future__ import annotations

import http.server
import os
import platform
import shutil
import socketserver
import sys
import webbrowser
from pathlib import Path


def _find_ui_dir() -> Path:
    """Locate the ``ui/`` directory relative to the repository root."""
    # When running from an installed package the repo root is two levels up
    # from src/sfcs_mdp/.  When running from a PyInstaller bundle the
    # bundled ``ui/`` sits next to the executable.
    candidates = [
        Path(__file__).resolve().parents[2] / "ui",
        Path(sys.executable).parent / "ui",
        Path.cwd() / "ui",
    ]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "launcher.html").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate ui/launcher.html.  "
        "Run this command from the repository root or pass --ui-dir."
    )


def _find_free_port(start: int = 8000, stop: int = 8100) -> int:
    """Return the first available TCP port in *start* .. *stop*."""
    import socket

    for port in range(start, stop):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}-{stop}")


# ------------------------------------------------------------------
# Hardware capability detection
# ------------------------------------------------------------------

def detect_hardware() -> dict[str, str]:
    """Return a dict of hardware hints that the front-end can consume.

    The values are intentionally kept as simple strings so they can be
    passed as URL query parameters.
    """
    info: dict[str, str] = {}

    info["cores"] = str(os.cpu_count() or 1)

    try:
        import struct
        info["arch_bits"] = str(struct.calcsize("P") * 8)
    except Exception:
        info["arch_bits"] = "64"

    info["platform"] = platform.system().lower()

    # Rough RAM estimate (Python has no portable way to query total RAM
    # but we can inspect *available* memory on some OSes).
    try:
        if platform.system() == "Windows":
            import ctypes

            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = _MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))  # type: ignore[attr-defined]
            info["ram_gb"] = str(round(mem.ullTotalPhys / (1024**3)))
        else:
            mem_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            info["ram_gb"] = str(round(mem_bytes / (1024**3)))
    except Exception:
        pass

    return info


# ------------------------------------------------------------------
# Browser helpers
# ------------------------------------------------------------------

_APP_BROWSERS: list[tuple[str, list[str]]] = [
    # (human name, possible executable names / paths)
    ("Microsoft Edge", ["msedge", "microsoft-edge", "microsoft-edge-stable"]),
    ("Google Chrome", ["chrome", "google-chrome", "google-chrome-stable", "chromium"]),
]

if platform.system() == "Windows":
    _EXTRA_PATHS: list[str] = [
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
        ),
        os.path.expandvars(
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
        ),
    ]
else:
    _EXTRA_PATHS = []


def _find_app_browser() -> str | None:
    """Return the path to a Chromium-based browser that supports ``--app``."""
    for _name, executables in _APP_BROWSERS:
        for exe in executables:
            path = shutil.which(exe)
            if path:
                return path
    for path_str in _EXTRA_PATHS:
        if os.path.isfile(path_str):
            return path_str
    return None


def _open_in_app_mode(url: str) -> bool:
    """Open *url* in a chromeless ``--app`` window.  Return True on success."""
    browser = _find_app_browser()
    if browser is None:
        return False

    import subprocess

    try:
        subprocess.Popen(  # noqa: S603
            [browser, f"--app={url}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except OSError:
        return False


# ------------------------------------------------------------------
# Server + launcher
# ------------------------------------------------------------------

def launch(
    ui_dir: Path | None = None,
    port: int | None = None,
    no_browser: bool = False,
) -> int:
    """Start a local server and open the studio in desktop mode.

    Returns 0 on clean shutdown, 1 on error.
    """
    try:
        serve_dir = ui_dir if ui_dir else _find_ui_dir()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not serve_dir.is_dir() or not (serve_dir / "launcher.html").is_file():
        print(
            f"ui directory not found or missing launcher.html: {serve_dir}",
            file=sys.stderr,
        )
        return 1

    if port is None:
        port = _find_free_port()

    hw = detect_hardware()
    qs = "&".join(f"{k}={v}" for k, v in hw.items())
    url = f"http://127.0.0.1:{port}/launcher.html?{qs}"

    _serve_dir = str(serve_dir)

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kw: object) -> None:
            kw["directory"] = _serve_dir
            super().__init__(*args, **kw)  # type: ignore[arg-type]

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # silence request logs

    try:
        httpd = socketserver.TCPServer(("127.0.0.1", port), _Handler)
    except OSError as exc:
        print(f"Cannot bind to port {port}: {exc}", file=sys.stderr)
        return 1

    print(f"Serving studio from {serve_dir}")
    print(f"  Desktop URL: {url}")

    if not no_browser:
        opened = _open_in_app_mode(url)
        if not opened:
            print("  (no Chromium browser found — opening default browser)")
            webbrowser.open(url)

    print("Press Ctrl+C to stop the server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("\nServer stopped.")
    return 0
