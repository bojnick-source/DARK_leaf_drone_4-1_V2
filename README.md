# DARK_leaf_drone_4-1_V2
impoved drone computational engineering software

## Manufacturing Digital Thread / Traveler Runner

The `sfcs-mdp` CLI validates and executes the SFCS manufacturing traveler in a deterministic,
auditable pipeline. String-based acceptance criteria require a manual signoff artifact.

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
