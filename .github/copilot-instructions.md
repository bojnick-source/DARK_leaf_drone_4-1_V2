# DARK_leaf_drone_4-1_V2 Project

## Project Overview
This is an improved drone computational engineering software repository that includes a manufacturing digital thread/traveler runner system. The project combines Python-based manufacturing process tooling (`sfcs-mdp`) with C++ computational engines for drone physics and control systems.

## Tech Stack

### Python Components
- **Language**: Python 3.11+ (targeting 3.12)
- **Build System**: setuptools
- **Key Dependencies**: 
  - pydantic 2.7.4 for data validation
  - PyYAML 6.0.2 for configuration parsing
- **Dev Tools**:
  - pytest 8.3.0 for testing
  - ruff 0.5.6 for linting
  - mypy 1.11.1 for type checking

### C++ Components
- **Language**: C++ 20 (standard required, no extensions)
- **Build System**: CMake 3.20+
- **Architecture**: Modular engine with external vendor code integration

### UI
- Static HTML/JavaScript dashboard in `ui/` directory
- Served via Python HTTP server for development

## Project Structure
- `src/sfcs_mdp/`: Manufacturing digital process CLI and core logic
- `src/reidce/`: Additional computational modules
- `v2/engine/`: C++ drone physics engine with tests
- `external/4-1-drone/`: Vendor code as isolated static library
- `manufacturing/`: SFCS traveler specifications and manufacturing data
- `tests/`: Python test suite
- `ui/`: Dashboard web interface
- `tools/`: Validation and utility scripts
- `docs/`: Project documentation

## Coding Standards

### Python Code Style
- **Line Length**: 100 characters (enforced by ruff)
- **Target Version**: Python 3.12
- **Linting**: Use ruff with checks: B (flake8-bugbear), E (pycodestyle errors), F (pyflakes), I (isort)
- **Type Checking**: Use mypy with strict configuration
- **Testing**: All tests use pytest
- **Imports**: Sorted and organized using isort rules

### C++ Code Style
- **Standard**: C++20 only, no compiler extensions
- **File Organization**: Separate header/implementation files
- **Testing**: Use CMake's enable_testing() framework
- **Module Structure**: Tests live in parallel test directories

### File Naming Policy
**Critical**: Follow the documented naming policy in `docs/naming_policy.md`:
- **Executable main files** (entry points, CLI programs, test harnesses with main): Use `ALL_CAPS.ext`
- **Sub files** (modules, helpers, implementations): Use `lower_snake_case.ext`
- **Tool-mandated files**: Keep as-is (`CMakeLists.txt`, `README.md`, `.github/` files)
- **History preservation**: Always use `git mv` for renames
- **Determinism**: No functional changes in rename batches

### Python Module and Variable Naming
- **Modules/packages**: `lower_snake_case`
- **Functions**: `lower_snake_case`
- **Variables**: `lower_snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`

## Manufacturing Digital Process (sfcs-mdp)

### CLI Commands
The `sfcs-mdp` tool provides these commands:
- `validate`: Validates manufacturing traveler specifications
- `run`: Executes the manufacturing traveler pipeline
- `simulate`: Runs in simulated mode for testing (creates dummy evidence)
- `status`: Checks build status
- `package`: Creates acceptance data package when all gates pass
- `color-qa`: Evaluates color quality assurance reports

### Key Concepts
- **Digital Thread**: Deterministic, auditable manufacturing pipeline
- **Build ID**: Unique identifier for each manufacturing run
- **Rev Tag**: Revision/version identifier
- **Block Level**: Manufacturing process stage (defaults to `BLOCK_0_STRUCTURE_ONLY`)
- **Simulated Mode**: Development/testing mode that creates dummy artifacts and `SIMULATION_NOTICE.txt`

## Testing

### Python Testing
- Framework: pytest
- Run tests: `python -m pytest`
- All new Python features should include unit tests
- Test files follow pattern: `tests/test_*.py`

### C++ Testing
- Framework: CMake's built-in testing
- Test files located in `v2/engine/tests/`
- Categories: sampling, calibration, physics, safety, core, validity, uncertainty
- Test naming: `*_test.cpp`

### Continuous Integration
- Defined in `.github/workflows/ci.yaml`
- Steps: Install dependencies → Lint (ruff) → Type check (mypy) → Test (pytest) → Validate mathlib

## Patterns and Conventions

### Python
- Use Pydantic models for data validation and configuration
- CLI built with standard argparse patterns
- Strong typing with type hints throughout
- Explicit error handling with clear error messages

### C++
- Modular architecture with clear separation of concerns
- Vendor code isolated in `external/` subdirectory
- Testing at multiple levels: unit (sampling, physics) and integration (safety, validity)

## Security and Quality

### Dependencies
- Pin exact versions in `pyproject.toml` for reproducibility
- Vendor C++ code managed as git submodule or subdirectory
- No secrets in code or configuration files

### Error Handling
- Clear error messages for validation failures
- Deterministic behavior in manufacturing pipeline
- Audit trail for manufacturing operations

### Quality Gates
- All code must pass linting (ruff for Python)
- All code must pass type checking (mypy for Python)
- All tests must pass before merge
- Manufacturing validation must complete successfully

## Key Documentation
- `docs/naming_policy.md`: File naming conventions and rename procedures
- `docs/rename_plan.md`: Migration planning documentation
- `README.md`: User-facing documentation with CLI examples
- `manufacturing/`: Contains SFCS specifications and mathlib validation

## Important Notes
- Manufacturing operations require explicit build ID and revision tags
- Simulated builds are clearly marked and not for production use
- Package creation only succeeds when all quality gates pass
- UI dashboard served locally for development/testing
- Color QA requires ICC profile metadata or sRGB fallback
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
