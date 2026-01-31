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

CLI commands append the numeric grading footer to each substantive output, including failures.
