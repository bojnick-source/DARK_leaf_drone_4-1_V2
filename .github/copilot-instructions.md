# Copilot Instructions for DARK_leaf_drone_4-1_V2

## Project Overview

This repository contains improved drone computational engineering software with:
- **Python CLI tool** (`sfcs-mdp`): Manufacturing digital thread traveler runner
- **C++ engine**: Drone physics simulation components
- **UI**: Daily dashboard for monitoring and QA

## Repository Structure

- `src/sfcs_mdp/`: Python CLI source code
- `src/reidce/`: Additional Python modules
- `v2/engine/`: C++ v2 engine implementation
- `external/4-1-drone/`: Vendor C++ code as isolated static library
- `tests/`: pytest test suite
- `manufacturing/`: Manufacturing specifications and mathlib
- `ui/`: Dashboard UI (static HTML/CSS/JS)
- `docs/`: Documentation including naming policy

## Development Workflow

### Python Development

1. **Install dependencies**:
   ```bash
   python -m pip install --upgrade pip
   python -m pip install .[dev]
   ```

2. **Lint code**:
   ```bash
   python -m ruff check .
   ```

3. **Type check**:
   ```bash
   python -m mypy src
   ```

4. **Run tests**:
   ```bash
   python -m pytest
   ```

5. **CLI usage**:
   ```bash
   sfcs-mdp validate --spec manufacturing/sfcs_drone_mdp_v0.yaml
   sfcs-mdp run --spec manufacturing/sfcs_drone_mdp_v0.yaml --build-id BUILD_0001 --rev-tag REV_A
   ```

### C++ Development

1. **Build system**: CMake (minimum 3.20)
2. **Standard**: C++20
3. **Structure**:
   - External vendor code in `external/4-1-drone/`
   - V2 engine in `v2/engine/`

### CI/CD

The CI pipeline (`.github/workflows/ci.yaml`) runs:
1. Python linting with ruff
2. Type checking with mypy
3. pytest test suite
4. mathlib validation

## Coding Standards

### Naming Policy

Following the documented naming policy in `docs/naming_policy.md`:

1. **Executable main files**: Use `ALL_CAPS.ext` (e.g., `CLOSEOUT_DEMO.cpp`)
2. **Sub files** (module internals): Use `lower_snake_case.ext` (e.g., `hover_momentum.cpp`)
3. **Directories**: Maintain existing structure
4. **History preservation**: Use `git mv` for renames
5. **Tool-mandated files**: Keep as-is (`CMakeLists.txt`, `README.md`, `.github/` contents)

### Python Standards

- **Line length**: 100 characters (configured in `pyproject.toml`)
- **Target version**: Python 3.12
- **Linting**: ruff with rules B, E, F, I
- **Type hints**: Required (checked with mypy)
- **Dependencies**:
  - Runtime: pydantic 2.7.4, PyYAML 6.0.2
  - Dev: pytest 8.3.0, ruff 0.5.6, mypy 1.11.1

### C++ Standards

- **Standard**: C++20 (required)
- **Extensions**: OFF
- **Vendor isolation**: External code stays in `external/` as static library

## Key Commands Reference

```bash
# Python setup and testing
pip install .[dev]
ruff check .
mypy src
pytest

# Manufacturing CLI
sfcs-mdp validate --spec manufacturing/sfcs_drone_mdp_v0.yaml
sfcs-mdp run --spec <spec> --build-id <id> --rev-tag <tag>
sfcs-mdp simulate --spec <spec> --build-id <id> --rev-tag <tag>
sfcs-mdp status --build-id <id>
sfcs-mdp package --build-id <id>
sfcs-mdp color-qa --report <path>

# UI preview
cd ui && python -m http.server
# Then open http://localhost:8000/dashboard.html

# Validate mathlib
python3 tools/validate_mathlib_v0.py manufacturing/mathlib_v0.yaml
```

## Testing Guidelines

- All tests use pytest framework
- Test files in `tests/` directory
- Key test modules:
  - `test_cli.py`: CLI command testing
  - `test_color_qa.py`: Color QA validation
  - `test_reidce_pico_topology.py`: REIDCE topology tests
  - `test_runner_simulate.py`: Simulation runner tests
  - `test_validate.py`: Validation logic tests
  - `test_ui_assets.py`: UI asset tests

## Best Practices

1. **Minimal changes**: Make surgical, focused modifications
2. **Test first**: Understand existing test infrastructure before changes
3. **Follow naming policy**: Adhere to documented naming conventions
4. **Preserve history**: Use `git mv` for file renames
5. **Run CI locally**: Lint, type-check, and test before committing
6. **Documentation**: Update relevant docs when changing functionality
7. **Vendor code**: Do not modify `external/` directory
8. **Type safety**: Add type hints to Python code
9. **Line length**: Respect 100-character limit

## Common Tasks

### Adding Python Dependencies

Update `pyproject.toml` under `dependencies` or `dev` optional dependencies, then:
```bash
pip install .[dev]
```

### Adding Tests

1. Create test file in `tests/` with `test_` prefix
2. Use pytest conventions
3. Run with `pytest` to verify

### Modifying CLI Commands

1. Edit `src/sfcs_mdp/cli.py`
2. Update help text and argument parsing
3. Add tests in `tests/test_cli.py`
4. Verify with `sfcs-mdp --help`

### Working with Manufacturing Specs

- Specs in YAML format in `manufacturing/`
- Validate with `sfcs-mdp validate --spec <path>`
- Update mathlib in `manufacturing/mathlib_v0.yaml`
- Validate mathlib with `python3 tools/validate_mathlib_v0.py`

## Security & Quality

- Run all linters and type checkers before committing
- Ensure tests pass locally
- Review CI failures promptly
- Do not introduce security vulnerabilities
- Follow secure coding practices for Python and C++
