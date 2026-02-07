#!/usr/bin/env python3
import json
import pathlib
import re
import sys

ID_PATTERN = re.compile(r"\b(?:REQ|PO|BENCH|SEC)-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}\b")


def extract_ids(path: pathlib.Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(ID_PATTERN.findall(text))


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    prompt_path = root / "docs" / "spec_prompt.txt"
    requirements_path = root / "docs" / "requirements.md"
    traceability_path = root / "docs" / "traceability.md"
    output_path = root / "runs" / "traceability.json"

    prompt_ids = extract_ids(prompt_path)
    requirement_ids = extract_ids(requirements_path)
    traceability_ids = extract_ids(traceability_path)

    missing_from_requirements = sorted(prompt_ids - requirement_ids)
    missing_from_traceability = sorted(requirement_ids - traceability_ids)
    extra_in_traceability = sorted(traceability_ids - requirement_ids)

    result = {
        "prompt_ids": sorted(prompt_ids),
        "requirement_ids": sorted(requirement_ids),
        "traceability_ids": sorted(traceability_ids),
        "missing_from_requirements": missing_from_requirements,
        "missing_from_traceability": missing_from_traceability,
        "extra_in_traceability": extra_in_traceability,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if missing_from_requirements or missing_from_traceability or extra_in_traceability:
        print("Traceability check failed:")
        if missing_from_requirements:
            print(f"Missing from requirements: {missing_from_requirements}")
        if missing_from_traceability:
            print(f"Missing from traceability: {missing_from_traceability}")
        if extra_in_traceability:
            print(f"Extra in traceability: {extra_in_traceability}")
        return 1

    print("Traceability check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
