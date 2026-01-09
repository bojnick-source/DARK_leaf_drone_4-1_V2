# FRAGMENT IO.0.4 — Run Artifact Loader & Validator (Authoritative Spec)

## Scope
- IO-only: read and validate previously emitted run artifacts.
- No physics/solvers/CLI/UI changes.
- Affects only `v2/engine/include/v2/io/`, optional `v2/engine/src/io/` (if needed), `v2/engine/tests/`, and `schemas/` (schema changes only if strictly required by validation).

## Goal
Provide deterministic loading and validation of a completed run’s artifacts written by IO.0.3. The loader must accept a `run_id` and an artifact root, verify integrity against the authoritative schema, and surface structured errors.

## Inputs
- `run_id` (expected): 16-char lowercase hex.
- `artifact_root`: repository-root–relative path to `artifacts/runs/<run_id>`.
- Required file: `artifacts/runs/<run_id>/run_output.json`.

## Validation Rules
1. The directory name `<run_id>` and the `run_output.json.run_id` **must match** the provided `run_id`; mismatch is an error.
2. Validate `run_output.json` against `schemas/run_output.schema.json`.
3. `ok` vs `label`:
   - When `ok == true`, `label` must be `null`.
   - When `ok == false`, `label` must be one of the `FailLabel` enum string values.
4. `inputs` must be an object; no additional validation beyond schema, but preserve canonical ordering on re-emit (reuse IO.0.2 canonicalization utilities).
5. `metrics` values must all be finite JSON numbers; reject NaN/inf or non-numeric types.
6. `artifacts` (optional):
   - `root` defaults to `artifacts/runs/<run_id>` when absent; otherwise must be a string.
   - `paths` (array of strings) must be **relative** (no absolute paths, no `..` segments). Presence of files is not enforced in IO.0.4 (best-effort check is allowed but not required).
7. Reject unknown top-level fields.

## Loader Behavior
- Provide a single public API (header-first) to load and validate:
  - Input: `run_id`, `artifact_root` (default `artifacts/runs/<run_id>`), optional strictness flag (default strict = true).
  - Output: strongly typed struct containing `run_id`, `ok`, `label` (optional), `inputs`, `metrics`, `artifacts` metadata.
- Deterministic parsing: use stable key ordering when re-serializing for tests or downstream use.
- Error handling: return rich error enum/category with messages for (a) missing file, (b) invalid JSON, (c) schema violation, (d) run_id mismatch, (e) invalid metrics, (f) invalid artifact paths.

## Tests
- Add unit tests under `v2/engine/tests/` that cover:
  - Successful load of a valid IO.0.3 artifact (happy path).
  - Rejection on run_id mismatch (dir vs JSON).
  - Rejection on invalid label with `ok == false`.
  - Rejection on non-finite metric values.
  - Rejection on artifact paths containing absolute or `..`.

## Out of Scope
- No new artifact files are written in IO.0.4.
- No changes to IO.0.3 writer behavior beyond validation compatibility.
- No CLI or solver integration.

## Normative Clarifications (Final)
1. The `run_id` **MUST** be exactly 16 lowercase hexadecimal characters; any deviation (length, casing, non-hex glyphs) **SHALL** be rejected before file I/O.
2. The loader **MUST** resolve the manifest path strictly as `<artifact_root>/run_output.json`; it **SHALL NOT** search alternate locations or fall back to other filenames.
3. Schema validation **MUST** use the repository-local `schemas/run_output.schema.json`; remote or embedded schemas **SHALL NOT** be substituted, and validation **MUST** reject unknown top-level fields.
4. When `strict == true`, artifact path entries **MUST** be rejected if absolute or containing `..`; when `strict == false`, the same normalization **SHALL** still occur, but offending entries **MUST** be reported while the remainder **MAY** be retained for inspection.
5. Metrics values **MUST** be JSON numbers representable as finite double precision; integers are allowed, but any NaN/Inf sentinel or non-numeric type **SHALL** fail validation.
6. Re-serialization of loaded inputs/metrics for testing or downstream use **MUST** reuse the IO.0.2 canonical ordering and formatting; array element order **SHALL NOT** be altered.
7. Each distinct failure condition **MUST** map to a stable, machine-consumable error code (e.g., MISSING_FILE, JSON_PARSE_ERROR, SCHEMA_VIOLATION, RUN_ID_MISMATCH, INVALID_METRIC, INVALID_ARTIFACT_PATH) and **SHALL** include a human-readable message.
