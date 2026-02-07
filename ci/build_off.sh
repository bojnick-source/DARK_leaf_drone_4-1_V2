#!/usr/bin/env bash
set -euo pipefail
cmake -S . -B build_off -DENABLE_V2_ENGINE=OFF -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build_off
TOPOPT_BUILD_MODE=OFF python - <<'PY'
import importlib
try:
    importlib.import_module("topopt.optional_heavy")
    raise SystemExit("Heavy optional dependency should not import in build_off mode.")
except ImportError:
    print("build_off optional dependency check passed.")
PY
