# Copilot Repository Instructions

## Overview

This repository contains the DARK_leaf_drone_4-1_V2 project - improved drone computational engineering software with a manufacturing digital thread/traveler runner system.

## Tech Stack

### Languages & Frameworks
- **Python**: 3.11+ minimum, 3.12 target (primary language for CLI and tools)
- **C++**: C++20 (for physics engine and performance-critical components)
- **CMake**: 3.20+ (build system for C++ components)

### Key Dependencies
- Python: `pydantic` (2.7.4), `PyYAML` (6.0.2)
- Development tools: `pytest`, `ruff`, `mypy`

## Project Structure

- `src/sfcs_mdp/` - Main Python package for SFCS manufacturing digital thread
- `src/reidce/` - REIDCE component
- `tests/` - Test suite (pytest-based)
- `v2/engine/` - V2 C++ physics engine
- `external/4-1-drone/` - Vendor code (isolated static library)
- `manufacturing/` - Manufacturing specifications and configurations
- `ui/` - Dashboard UI (static HTML/JS)
- `tools/` - Build and validation tools
- `python/tools/v2/` - V2-specific Python tools

## Build and Test Commands

### Python Components

```bash
# Install dependencies (including dev tools)
python -m pip install .[dev]

# Run linter (ruff)
python -m ruff check .

# Run type checker (mypy)
python -m mypy src

# Run tests
python -m pytest

# Validate mathlib
python3 tools/validate_mathlib_v0.py manufacturing/mathlib_v0.yaml
```

### C++ Components

```bash
# Configure and build
cmake -S . -B build
cmake --build build

# Run tests
ctest --test-dir build
```

### Manufacturing Digital Thread (sfcs-mdp CLI)

```bash
# Validate spec
sfcs-mdp validate --spec manufacturing/sfcs_drone_mdp_v0.yaml

# Run traveler
sfcs-mdp run --spec manufacturing/sfcs_drone_mdp_v0.yaml --build-id BUILD_0001 --rev-tag REV_A

# Simulated build mode (development/testing)
sfcs-mdp simulate --spec manufacturing/sfcs_drone_mdp_v0.yaml --build-id BUILD_0001 --rev-tag REV_A

# Check status and package
sfcs-mdp status --build-id BUILD_0001
sfcs-mdp package --build-id BUILD_0001
```

### UI Development

```bash
cd ui
python -m http.server
# Then open http://localhost:8000/dashboard.html
```

## Coding Conventions

### Python
- **Python version**: 3.11+ minimum, 3.12 for development/tooling
- **Line length**: 100 characters (enforced by ruff)
- **Linting**: Use ruff with select rules ["B", "E", "F", "I"], targeting Python 3.12
- **Type checking**: Required with mypy for Python 3.12 (ignore missing imports allowed)
- Follow existing patterns in `src/sfcs_mdp/` and `src/reidce/`
- Use `pydantic` for data validation and configuration models
- Prefer type hints on all functions

### C++
- **Standard**: C++20, no compiler extensions
- **Naming**: Follow existing conventions in `v2/engine/` and `external/4-1-drone/`
- Keep vendor code (`external/4-1-drone/`) isolated as a static library
- Do not modify vendor code unless absolutely necessary

### General
- Always run linters and tests before committing changes
- Keep commits focused and minimal
- Update documentation when changing CLI interfaces or APIs

## Manufacturing Domain Context

This project implements a deterministic, auditable manufacturing traveler pipeline (SFCS - Shop Floor Control System). Key concepts:

- **Digital Thread**: Traceable record of manufacturing steps and evidence
- **Traveler**: Manufacturing process specification with acceptance criteria
- **Block Levels**: Progressive stages (e.g., `BLOCK_0_STRUCTURE_ONLY`)
- **Evidence & Signoffs**: Required for gate passage and packaging
- **Simulation Mode**: Development/testing mode with dummy evidence (creates `SIMULATION_NOTICE.txt`)

String-based acceptance criteria require manual signoff artifacts. Packaging only produces `acceptance_data_package.zip` when all gates pass.

## Important Notes

- Do not modify files in `external/4-1-drone/` without explicit instruction (vendor code)
- Manufacturing specs in `manufacturing/` are critical - validate any changes with mathlib validator
- The `records/` and `quality/ncr/` directories are in `.gitignore` - runtime data only
- UI is static HTML/JS - keep it simple and preview changes locally
- Color QA reports must include ICC profile metadata or sRGB fallback

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yaml`) runs:
1. Python linting (ruff)
2. Type checking (mypy)
3. Test suite (pytest)
4. Mathlib validation

All checks must pass before merging.
