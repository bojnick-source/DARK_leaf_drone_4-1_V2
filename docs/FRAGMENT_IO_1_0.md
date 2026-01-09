# FRAGMENT IO.1.0 — Multi-Run Artifact Ingest & Indexer (Authoritative Spec)

## Scope (Spec Only — No Code)
- IO-only ingestion of multiple run artifacts previously written by IO.0.x.
- No physics/solvers/CLI/UI changes.
- Affects future work in `v2/engine/include/v2/io/`, optional `v2/engine/src/io/`, `v2/engine/tests/`, and `schemas/` (schema changes only if strictly required).

## Goal
Define how to ingest, validate, and index **multiple** completed runs located under `artifacts/runs/`, producing a deterministic in-memory representation and optional summary index.

## Inputs
- `artifact_root`: repository-root–relative path to `artifacts/runs/` (default).
- Optional filters:
  - `run_ids`: explicit allowlist of 16-char lowercase hex run_ids.
  - `glob` / prefix filter for directories.
  - `max_runs` (non-negative integer) to cap ingestion.

## Required Behavior
1. **Directory Discovery**
   - Enumerate immediate child directories of `artifact_root`; each directory name **MUST** match the 16-char lowercase hex `run_id` pattern. Non-matching names **SHALL** be skipped and reported.
   - `run_output.json` **MUST** exist in each candidate directory; absence **SHALL** be reported and that run skipped.
2. **Per-Run Validation**
   - Each discovered run **MUST** be loaded and validated using the IO.0.4 loader/validator (strict mode by default).
   - `run_id` in the directory and JSON **MUST** match exactly; mismatches **SHALL** be treated as errors for that run.
   - Validation errors **SHALL** be collected per run with stable error codes; successful runs proceed to indexing.
3. **Deterministic Ordering**
   - Ingestion order **MUST** be deterministic: sort run_ids ascending lexicographically after filtering.
   - Any summary/index output **MUST** preserve this ordering.
4. **Summary/Index (Logical)**
   - Define a logical summary structure containing, at minimum: `run_id`, `ok`, `label` (if present), `metrics`, `artifact_root`, and `source_path` (`<artifact_root>/<run_id>/run_output.json`).
   - Unknown or additional fields are **NOT** added at this stage; pass-through of existing fields is allowed when explicitly covered by IO.0.4.
5. **Error Handling**
   - Distinct failure modes **MUST** map to stable error codes (e.g., INVALID_RUN_ID_DIR, MISSING_MANIFEST, VALIDATION_FAILED).
   - Ingest **SHALL** continue past invalid runs, aggregating results.

## Tests (Future)
- Unit tests **MUST** cover:
  - Ingestion with multiple valid runs producing deterministic ordering.
  - Skipping invalid directory names.
  - Handling missing `run_output.json`.
  - Propagating IO.0.4 validation errors for a subset of runs while succeeding on others.
  - Application of filters (`run_ids`, prefix/glob, `max_runs`).

## Out of Scope
- No new artifact writes.
- No aggregation of metrics beyond pass-through summarization.
- No CLI exposure in IO.1.0.
