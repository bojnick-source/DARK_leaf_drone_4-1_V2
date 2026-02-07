#!/usr/bin/env bash
set -euo pipefail
cmake -S . -B build_on -DENABLE_V2_ENGINE=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build_on
