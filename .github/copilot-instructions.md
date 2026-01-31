# GitHub Copilot Instructions for DARK_leaf_drone_4-1_V2

## Project Overview

This repository contains improved drone computational engineering software with two main components:

1. **Python CLI Tool (`sfcs-mdp`)**: Manufacturing digital thread/traveler runner for the SFCS (Smart Factory Control System)
2. **C++ Engine**: Drone physics and analysis engine with computational components

## Repository Structure

- `src/sfcs_mdp/` - Python CLI implementation for manufacturing digital thread
- `v2/engine/` - C++ v2 drone engine
- `external/4-1-drone/` - Vendored C++ code for legacy drone engine
- `manufacturing/` - YAML specifications for manufacturing processes
- `tests/` - Python test suite
- `ui/` - Dashboard UI (static HTML/JS)
- `tools/` - Validation scripts

## Code Style and Linting

### Python
- **Formatter/Linter**: Use `ruff` with line length 100
- **Type Checker**: Use `mypy` with Python 3.12 type hints
- **Python Version**: 3.11+ (target 3.12)
- Follow existing patterns in `src/sfcs_mdp/`
- Use Pydantic for data validation and models
- Keep functions focused and well-typed

### C++
- **Standard**: C++20
- **CMake**: Minimum version 3.20
- Follow existing patterns in `v2/engine/`
- Keep headers in `include/`, implementation in `src/`

## Testing

- **Framework**: pytest
- **Location**: All tests in `tests/` directory
- **Run tests**: `python -m pytest`
- **Add tests** for new CLI commands and validation logic
- Test files follow pattern `test_*.py`

## Build and Development

### Python Component
```bash
# Install with dev dependencies
python -m pip install .[dev]

# Lint code
python -m ruff check .

# Type check
python -m mypy src

# Run tests
python -m pytest

# Validate manufacturing spec
python3 tools/validate_mathlib_v0.py manufacturing/mathlib_v0.yaml
```

### C++ Component
```bash
# Build
mkdir build && cd build
cmake ..
make

# Run tests
ctest
```

### UI Preview
```bash
cd ui
python -m http.server
# Open http://localhost:8000/dashboard.html
```

## CLI Commands

The `sfcs-mdp` CLI provides several commands:

- `validate` - Validate manufacturing spec
- `run` - Execute manufacturing traveler
- `simulate` - Run in simulation mode (dev/testing)
- `status` - Check build status
- `package` - Package build artifacts
- `color-qa` - Evaluate color QA reports

Default spec location: `manufacturing/sfcs_drone_mdp_v0.yaml`

## Key Dependencies

### Python
- `pydantic==2.7.4` - Data validation
- `PyYAML==6.0.2` - YAML parsing

### Development
- `pytest==8.3.0` - Testing
- `ruff==0.5.6` - Linting
- `mypy==1.11.1` - Type checking

## Manufacturing Digital Thread

The manufacturing component implements a deterministic, auditable pipeline for SFCS drone production:

- Specs are YAML-based in `manufacturing/`
- Supports block-level execution and gating
- Creates evidence artifacts and signoffs
- Simulation mode for development/testing
- Packaging requires all gates to pass

## Important Notes

- **Minimal changes**: Make surgical, focused changes
- **Test coverage**: Add tests for new functionality
- **Type safety**: Always use type hints in Python
- **Validation**: Manufacturing specs must validate before use
- **Simulation**: Use `--simulate` flag for testing, never in production
- **Evidence**: All production runs must create proper evidence artifacts

## CI Pipeline

The CI runs on every push and PR:
1. Lint with ruff
2. Type check with mypy
3. Run pytest test suite
4. Validate mathlib spec

All checks must pass before merging.
