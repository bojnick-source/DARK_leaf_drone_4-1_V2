# DARK_leaf_drone_4-1_V2
impoved drone computational engineering software

## Scope (this PR)
Included:
- v2 deterministic core IO (run_id, artifact layout, canonicalization, JSON emission, error handling)
- v2 CLI entrypoint (`v2_cli`)
- deterministic gates implemented in code (accuracy, commit, lineage)
- python orchestration tools (`run_batch.py`, `parse_results.py`)
- minimal deterministic C++ tests and golden fixtures
- spec/manifest docs as documentation only (spec-only / not implemented here)

Not included (future work):
- Monte Carlo / uncertainty wrapper
- sampling proposals
- probabilistic safety gate
- calibration boundary layer
- validity/governance report layer

Build isolation:
- v2 targets are opt-in via `-DENABLE_V2_ENGINE=ON` (default OFF to preserve baseline builds).
## Getting Started

### Prerequisites

* **Python 3.11 or newer** – download from <https://www.python.org>.
  When installing on Windows make sure **"Add Python to PATH"** is checked.
* **Git** – to clone the repository.

### Clone and install

**PowerShell / Windows:**

```powershell
git clone https://github.com/bojnick-source/DARK_leaf_drone_4-1_V2.git
cd DARK_leaf_drone_4-1_V2
.\install.ps1          # installs sfcs-mdp so you can run it like an exe
```

To include development tools (pytest, ruff, mypy):

```powershell
.\install.ps1 -Dev
```

**Bash / macOS / Linux:**

```bash
git clone https://github.com/bojnick-source/DARK_leaf_drone_4-1_V2.git
cd DARK_leaf_drone_4-1_V2
pip install -e .       # or: pip install -e ".[dev]"
```

After installation, the `sfcs-mdp` command is available system-wide.

### Verify the installation

```powershell
python -m sfcs_mdp validate
```

If the spec file is found you will see `VALIDATION OK`.

## Manufacturing Digital Thread / Traveler Runner

The `sfcs-mdp` CLI validates and executes the SFCS manufacturing traveler in a deterministic,
auditable pipeline. String-based acceptance criteria require a manual signoff artifact.

The CLI can be invoked in two ways:

```bash
sfcs-mdp <command> [options]
```

```bash
python -m sfcs_mdp <command> [options]
```

The `python -m sfcs_mdp` form works on every shell including **PowerShell** and
**cmd.exe** on Windows, so use it if `sfcs-mdp` is not recognised.

### Validate the spec

```bash
sfcs-mdp validate --spec manufacturing/sfcs_drone_mdp_v0.yaml
```

If `--spec` is omitted, the CLI defaults to `manufacturing/sfcs_drone_mdp_v0.yaml` when it
exists; otherwise it exits with a clear error.

### Run the traveler

```bash
sfcs-mdp run --spec manufacturing/sfcs_drone_mdp_v0.yaml --build-id BUILD_0001 --rev-tag REV_A
```

If `--block-level` is omitted, the runner defaults to `BLOCK_0_STRUCTURE_ONLY`.

### Simulated build mode (development/testing only)

```bash
sfcs-mdp run --spec manufacturing/sfcs_drone_mdp_v0.yaml --build-id BUILD_0001 --rev-tag REV_A --simulate
```

```bash
sfcs-mdp simulate --spec manufacturing/sfcs_drone_mdp_v0.yaml --build-id BUILD_0001 --rev-tag REV_A
```

Simulated runs create dummy evidence and signoffs and write a `SIMULATION_NOTICE.txt` file
to clearly label the build as non-production.

### Check status and package

```bash
sfcs-mdp status --build-id BUILD_0001
sfcs-mdp package --build-id BUILD_0001
```

Packaging only produces `acceptance_data_package.zip` when all gates pass.

### PowerShell / Windows examples

If `sfcs-mdp` is not on your PATH or PowerShell does not recognise the command,
use `python -m sfcs_mdp` instead:

```powershell
python -m sfcs_mdp validate --spec manufacturing/sfcs_drone_mdp_v0.yaml
python -m sfcs_mdp simulate --build-id BUILD_0001 --rev-tag REV_A
python -m sfcs_mdp status --build-id BUILD_0001
python -m sfcs_mdp package --build-id BUILD_0001
```

## Daily Dashboard UI

The UI shell lives in `ui/` and can be previewed by running a static server:

```bash
cd ui
python -m http.server
```

Then open `http://localhost:8000/dashboard.html`.

### Evaluate color QA

```bash
sfcs-mdp color-qa --report path/to/color_profile_scene.json
```

The report must include ICC profile metadata (or sRGB fallback), output transform mode, and
the patch set required by the visual QA contract.
CLI commands append the numeric grading footer to each substantive output, including failures.
