# DARK_leaf_drone_4-1_V2
Improved drone computational engineering software — **Vibe Engineering Studio**

## Vibe Engineering Workflow

The DARK leaf Drone studio provides an end-to-end workflow for designing,
testing, and presenting drone builds:

1. **Install & Launch** — Run `install.ps1 -Shortcut` on Windows to install
   and create a desktop icon.  Open `ui/launcher.html` to start the studio.
2. **Project** — Create a new project or import data (STEP, STL, JSON, YAML,
   images).  Drag & drop files into the project panel.
3. **Vibe Engineer** — Chat with the AI to describe your drone.  Mention
   components (frame, motor, propeller, battery, camera) and they get
   generated automatically.
4. **Assembly Lab** — Generated components are assembled by AI.  Validate
   the assembly for watertight/manifold mesh integrity.
5. **CAD Mesh Viewer** — High-fidelity 3D view of the assembled drone.
   Switch between high-fidelity and low-res editing modes.  Exploded view
   for inspection.
6. **Flight Simulation** — Background physics-based flight sim with a
   map-dot tracker, live telemetry gauges, and full telemetry dashboard.
7. **Presentation** — Disassemble and reassemble the drone in an animated
   "gun-table" style view for clients and investors.

### Quick Start

```bash
# Clone and install
git clone https://github.com/bojnick-source/DARK_leaf_drone_4-1_V2.git
cd DARK_leaf_drone_4-1_V2
pip install -e .          # or: .\install.ps1 on Windows

# Launch the studio
cd ui && python -m http.server
# Open http://localhost:8000/launcher.html
```

### Windows installer with desktop shortcut

```powershell
.\install.ps1 -Shortcut
# Creates "DARK leaf Drone" shortcut on your desktop
```

## Scope
Included:
- v2 deterministic core IO (run_id, artifact layout, canonicalization, JSON emission, error handling)
- v2 CLI entrypoint (`v2_cli`)
- deterministic gates implemented in code (accuracy, commit, lineage)
- python orchestration tools (`run_batch.py`, `parse_results.py`)
- minimal deterministic C++ tests and golden fixtures
- spec/manifest docs as documentation only (spec-only / not implemented here)
- Monte Carlo / uncertainty wrapper (`v2/engine/src/uncertainty/`)
- sampling proposals (`v2/engine/src/sampling/`)
- probabilistic safety gate (`v2/engine/src/safety/`)
- calibration boundary layer (`v2/engine/src/calibration/`)
- validity/governance report layer (`v2/engine/src/validity/`)

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

### Build a standalone EXE (Windows)

If you want a single `.exe` file that runs without needing Python installed:

```powershell
.\install.ps1 -Exe
```

Or manually:

```bash
pip install ".[exe]"
python build_exe.py
```

The executable is written to `dist/sfcs-mdp.exe` (or `dist/sfcs-mdp` on
Linux/macOS). Copy it anywhere and run it directly — no Python required on the
target machine.

### C++ engine (optional)

The repository also contains a C++ computational engine under `v2/engine/` and
`cpp/engine/`.  These components are **completely optional** — the Python
`sfcs-mdp` CLI works without compiling any C++ code.

If you want to build the C++ engine (requires a C++20 compiler and CMake 3.20+):

```bash
cmake -S . -B build -DENABLE_V2_ENGINE=ON
cmake --build build
ctest --test-dir build        # run the C++ tests
```

On Windows with Visual Studio:

```powershell
cmake -S . -B build -DENABLE_V2_ENGINE=ON
cmake --build build --config Release
ctest --test-dir build --build-config Release
```

Or use the install script:

```powershell
.\install.ps1 -Cpp
```

When `ENABLE_V2_ENGINE` is `OFF` (the default), CMake skips the C++ targets
entirely.

### Using Python + C++ together

Once the C++ engine is built, pass `--engine-cli` to the `run` or `simulate`
commands so the traveler pipeline calls the C++ engine and archives its output:

```bash
sfcs-mdp simulate --build-id BUILD_0001 --rev-tag REV_A \
    --engine-cli build/v2/engine/v2_engine_cli
```

The engine result is written to `records/builds/<build_id>/v2_engine_output.json`
and included in the ledger under the `v2_engine` key.

You can also call the engine directly:

```bash
sfcs-mdp engine --engine-cli build/v2/engine/v2_engine_cli \
    --canonical-input '{"alpha":"1.250000","beta":"2.500000"}'
```

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

The studio lives in `ui/` and can be previewed by running a static server:

```bash
cd ui
python -m http.server
```

Then open:
- **Studio (Vibe Engineering)**: `http://localhost:8000/launcher.html`
- **Daily Dashboard**: `http://localhost:8000/dashboard.html`
- **CAD Viewer**: `http://localhost:8000/cad_viewer.html`
- **Flight Sim Telemetry**: `http://localhost:8000/flight_sim.html`

### Evaluate color QA

```bash
sfcs-mdp color-qa --report path/to/color_profile_scene.json
```

The report must include ICC profile metadata (or sRGB fallback), output transform mode, and
the patch set required by the visual QA contract.
CLI commands append the numeric grading footer to each substantive output, including failures.
