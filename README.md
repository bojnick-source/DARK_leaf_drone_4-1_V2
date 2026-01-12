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
