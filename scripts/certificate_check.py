#!/usr/bin/env python3
import json
import pathlib
import sys

REQUIRED_FIELDS = [
    "run_id",
    "overall_status",
    "lhs_enabled",
    "n_samples",
    "seed",
    "batching_mode",
    "lhs_quality_metrics",
    "uq_mode_verdict",
]


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: certificate_check.py <results_certificate.json>")
        return 2
    path = pathlib.Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        print(f"Missing required fields: {missing}")
        return 1
    if data.get("overall_status") != "VERIFIED":
        print("Certificate status is not VERIFIED.")
        return 1
    print("Certificate check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
