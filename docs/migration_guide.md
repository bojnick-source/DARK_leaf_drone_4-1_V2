# Migration guide

## Scope
This upgrade introduces a new `topopt` CLI and UQ sampling utilities without removing existing functionality. Existing CMake and Python workflows remain intact.

## Backward compatibility
- Existing binaries and tests continue to run unchanged.
- New tooling is additive and lives under `/src/topopt` and `/scripts`.

## Integration boundaries
- PicoGK/Noyron/Freeform integrations are implemented as adapters/placeholders only (REQ-LEAP-002).
- Open fallback geometry uses SDF + marching cubes placeholders for end-to-end runs (REQ-LEAP-003).
- No proprietary internals are copied or re-created (SEC-LIC-001, SEC-LIC-002).

## Precision backend selection
- Python provides the default fast analytic proxy for CI-small runs.
- Set `TOPOPT_PRECISION_BACKEND=cpp` after building to enable the C++ precision backend binary.

## Simplifications and disclosures
- The reference solver used for CI-small benchmarks is an analytic proxy; it is recorded explicitly in results outputs to avoid silent physics weakening (REQ-MIS-004).

## ID policy scope
The must/shall ID policy is enforced for new TopOpt docs/scripts; spec_prompt.txt remains verbatim and legacy fragments are excluded from scanning.

## How to run
1. `topopt repo-check`
2. `topopt uq sample --method lhs --n 16 --out runs/samples.parquet`
3. `topopt bench --benchmark mbb --config configs/default_parameters.json`
4. `topopt certify --run-id <run-id>`
5. `topopt viz --run-id <run-id>`
