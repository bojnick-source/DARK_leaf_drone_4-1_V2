#!/usr/bin/env bash
set -euo pipefail

topopt bench --benchmark mbb --config configs/default_parameters.json
RUN_ID=$(ls -1t runs | head -n 1)

topopt certify --run-id "$RUN_ID"
python scripts/certificate_check.py "runs/$RUN_ID/results_certificate.json"

topopt viz --run-id "$RUN_ID"
