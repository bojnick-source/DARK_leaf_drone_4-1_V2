# v2 Computational Engineering Scaffold

This directory documents the v2 “truth-layer” engine and Qt-based studio scaffold. The current state is a minimal, build-safe foundation that will grow to host deterministic physics, validation, and desktop UI workflows.

## Scope
- **v2 engine**: C++ library (`v2_engine`) and CLI (`v2_engine_cli`) for deterministic calculations and validation. Failure classification lives in `v2/engine/include/v2/core/fail_label.hpp`.
- **v2 studio**: Qt 6 desktop application (`v2_studio`) intended to host high-fidelity graphics, CAD, and workflow orchestration. When Qt 6 is unavailable, a non-Qt placeholder binary is built to keep configuration deterministic.
- **Schemas**: Live under `schemas/` and will define structured inputs/outputs for fragment execution.

## Build (CMake)
```bash
mkdir -p build
cmake -S . -B build
cmake --build build
```

### Qt Notes
- `V2_STUDIO_ENABLE_QT` (ON by default) attempts to find Qt6 Core/Gui/Widgets.
- If Qt6 is not found, configuration stays build-safe and produces a placeholder `v2_studio` without Qt dependencies.
