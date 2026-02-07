#!/usr/bin/env python3
import pathlib
import re
import sys

ID_PATTERN = re.compile(r"\b(?:REQ|PO|BENCH|SEC)-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}\b")
KEYWORDS = ("MUST", "SHALL")  # REQ-TRACE-002

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "build-ON",
    "build-OFF",
    "build_on",
    "build_off",
    "external",
    "legacy",
    "ui",
}
EXCLUDE_FILES = {pathlib.Path("docs/spec_prompt.txt")}
INCLUDE_EXTS = {".md", ".txt", ".py", ".yml", ".yaml", ".toml", ".json", ".sh"}
INCLUDE_ROOTS = {
    pathlib.Path("docs"),
    pathlib.Path("scripts"),
    pathlib.Path("ci"),
}


def should_scan(path: pathlib.Path) -> bool:
    if path in EXCLUDE_FILES:
        return False
    if path.name.startswith("FRAGMENT_"):
        return False
    if not any(path.is_relative_to(root) for root in INCLUDE_ROOTS):
        return False
    if path.suffix not in INCLUDE_EXTS:
        return False
    return True


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    violations: list[str] = []
    for path in root.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.is_file() and should_scan(path.relative_to(root)):
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for idx, line in enumerate(content.splitlines(), start=1):
                if any(keyword in line for keyword in KEYWORDS):
                    if not ID_PATTERN.search(line):
                        violations.append(f"{path}:{idx}: {line}")
    if violations:
        print("must/shall ID violations found:")
        print("\n".join(violations))
        return 1
    print("must/shall ID check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
