from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from v2.python.engine.v2_run_manifest import (
    FailLabel,
    LoadError,
    SummaryOptions,
    aggregate_runs,
    canonicalize_inputs,
    load_run_output,
    run_id_from_inputs,
    write_run_output,
)


def test_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    scalars = {"mass": 1.0, "area": 0.5}
    arrays = {"vec": [1.0, 2.0]}
    units = {"length": (1.0, "m")}
    rid = run_id_from_inputs(scalars, {}, arrays, units)
    inputs_json = canonicalize_inputs(scalars, {}, arrays, units)

    p = write_run_output(rid, inputs_json, {"energy": 42.5}, True, None, ["extra.dat"])
    assert Path(p).exists()

    lr = load_run_output(rid)
    assert lr.success and lr.code == LoadError.NONE and lr.output
    assert lr.output.run_id == rid
    assert lr.output.ok is True
    assert lr.output.metrics["energy"] == 42.5
    assert lr.output.artifact_paths == ["extra.dat"]


def test_strict_path_portable_rejects_windowsy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rid = "1234567890abcdef"
    inputs_json = "{}"
    with pytest.raises(ValueError):
        write_run_output(rid, inputs_json, {}, True, None, ["..\\bad"])
    with pytest.raises(ValueError):
        write_run_output(rid, inputs_json, {}, True, None, ["C:evil.txt"])
    with pytest.raises(ValueError):
        write_run_output(rid, inputs_json, {}, True, None, ["../bad"])


def test_aggregate_counts_and_label_tally(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    r1 = "aaaaaaaaaaaaaaaa"
    r2 = "bbbbbbbbbbbbbbbb"
    inputs_json = "{}"

    write_run_output(r1, inputs_json, {"energy": 5.0}, True)
    write_run_output(r2, inputs_json, {}, False, FailLabel.SYS_NAN_FAIL)

    (Path("artifacts") / "runs" / "bad_dir").mkdir(parents=True, exist_ok=True)

    summ = aggregate_runs(SummaryOptions(generated_at="2024-01-01T00:00:00Z"))
    assert summ.counts.total == 3
    assert summ.counts.passed == 1
    assert summ.counts.failed == 1
    assert summ.counts.invalid == 1
    assert '"label_tally":{"SYS_NAN_FAIL":1}' in summ.json


def _find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for _ in range(30):
        if (p / "pyproject.toml").exists() or (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise RuntimeError("repo root not found")


def _find_header(repo_root: Path) -> Path:
    hits = list(repo_root.rglob("run_manifest.hpp"))
    if not hits:
        raise RuntimeError("run_manifest.hpp not found")
    hits.sort(key=lambda x: len(str(x)))
    return hits[0]


def _include_root_from_header(h: Path) -> Path:
    parts = list(h.parts)
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == "include":
            return Path(*parts[: i + 1])
    return h.parent.parent.parent


def test_cpp_parity_if_available(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__).parent)
    header = _find_header(repo_root)
    inc = _include_root_from_header(header)

    compiler = None
    for c in ("c++", "g++", "clang++"):
        result = subprocess.call(
            [c, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if result == 0:
            compiler = c
            break
    if compiler is None:
        raise RuntimeError("C++ compiler not found (required for parity test)")

    src = tmp_path / "parity.cpp"
    exe = tmp_path / "parity"

    # best-effort include path: prefer "v2/io/run_manifest.hpp" if present under include root
    rel = None
    try:
        rel = header.relative_to(inc).as_posix()
    except Exception:
        rel = header.as_posix()

    src.write_text(
        r'''
#include <iostream>
#include <string>
#include <map>
#include <vector>
#include <cmath>

#include "'''
        + rel
        + r'''"

int main() {
    using v2::io::run_id_from_inputs;
    using v2::io::canonicalize_inputs;
    using v2::io::format_scalar;

    std::map<std::string, double> scalars{{"mass", 1.0}, {"area", 0.5}};
    std::map<std::string, std::string> text;
    std::map<std::string, std::vector<double>> arrays{{"vec", {1.0, 2.0}}};
    std::map<std::string, std::pair<double, std::string>> units{{"length", {1.0, "m"}}};

    auto rid = run_id_from_inputs(scalars, text, arrays, units);
    auto inputs = canonicalize_inputs(scalars, text, arrays, units);
    auto scalar = format_scalar(42.5);

    std::cout << rid << "\n";
    std::cout << inputs << "\n";
    std::cout << scalar << "\n";

    return 0;
}
'''
    )

    # Compile C++ parity test
    compile_cmd = [compiler, "-std=c++20", f"-I{inc}", str(src), "-o", str(exe)]
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(f"C++ compilation failed:\n{result.stderr}")

    # Run C++ executable
    cpp_result = subprocess.run([str(exe)], capture_output=True, text=True, cwd=tmp_path)
    if cpp_result.returncode != 0:
        pytest.fail(f"C++ execution failed:\n{cpp_result.stderr}")

    cpp_lines = cpp_result.stdout.strip().split("\n")
    assert len(cpp_lines) == 3

    # Compare Python and C++ outputs
    from v2.python.engine.v2_run_manifest import (
        canonicalize_inputs,
        format_scalar,
        run_id_from_inputs,
    )

    scalars = {"mass": 1.0, "area": 0.5}
    arrays = {"vec": [1.0, 2.0]}
    units = {"length": (1.0, "m")}

    py_rid = run_id_from_inputs(scalars, {}, arrays, units)
    py_inputs = canonicalize_inputs(scalars, {}, arrays, units)
    py_scalar = format_scalar(42.5)

    assert cpp_lines[0] == py_rid, f"run_id mismatch: C++={cpp_lines[0]}, Python={py_rid}"
    assert cpp_lines[1] == py_inputs, f"inputs mismatch: C++={cpp_lines[1]}, Python={py_inputs}"
    assert cpp_lines[2] == py_scalar, f"scalar mismatch: C++={cpp_lines[2]}, Python={py_scalar}"
