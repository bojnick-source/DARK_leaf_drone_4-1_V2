# FRAGMENT IO.1.1 — Aggregation & Summary Export (Authoritative Spec)

## Scope (Spec Only — No Code)
- Build atop IO.1.0 ingest to aggregate multiple runs into deterministic summary artifacts.
- Covers manifest index generation and canonical summary JSON.
- No physics/solvers/CLI changes; no schema writes beyond what is specified here.

## Inputs
- `artifact_root`: path to `artifacts/runs/` (repository-root–relative unless otherwise provided).
- Optional filters (applied before aggregation):
  - `run_ids` allowlist.
  - Prefix/glob filter.
  - `max_runs` cap (non-negative integer), applied after sorting/filtering.

## Duplicate run_id Precedence
- If multiple candidate sources map to the same `run_id` (e.g., duplicate directories or staged overlays), the aggregator **MUST** pick exactly one source deterministically.
- Precedence rule (in order):
  1. Most recent `run_output.json` `mtime` wins.
  2. If `mtime` ties, lexicographically smallest absolute manifest path wins.
- Non-selected duplicates **SHALL** be recorded as errors with code `DUPLICATE_RUN_ID` and included in the summary error list.

## Processing & Determinism
- Candidate runs **MUST** be discovered and filtered as in IO.1.0.
- Selected manifests **MUST** be validated via IO.0.4 strict mode before aggregation.
- All ordering **SHALL** be deterministic: run_ids sorted ascending after deduplication; summary sections preserve this order.
- Aggregation **MUST** be side-effect-free (read-only).

## Summary JSON (Canonical Output)
- The canonical summary JSON **SHALL** be a single object with the following top-level fields:
  - `schema`: string identifier for this summary format (e.g., `dark/v2/io/run_summary/1.1`).
  - `artifact_root`: absolute or repo-relative path used for ingestion.
  - `generated_at`: RFC 3339 UTC timestamp.
  - `runs`: array ordered by run_id ascending, each entry:
    - `run_id` (string, 16-char hex)
    - `ok` (boolean)
    - `label` (string; optional, only when present in manifest)
    - `metrics` (object; optional, passthrough from manifest when ok)
    - `source_path` (string; absolute or repo-relative path to `run_output.json`)
    - `error` (object; optional, only when `ok` is false) with `code` (string) and `message` (string)
  - `counts`: object with `total`, `passed`, `failed`, `invalid` (non-negative integers; `invalid` counts validation/ingest errors, including duplicates).
  - `label_tally`: object mapping `label` => count for all runs with `ok == true` and label present; omitted or empty when none.
  - `errors`: array of error objects (ordered by run_id, then code) for any skipped/failed runs, including duplicates and validation failures. Each error has `run_id`, `code`, `message`, and optional `source_path`.

## Error Handling for Partial Runs
- Aggregation **MUST** continue when a subset of runs fail validation or are skipped.
- A run with missing `run_output.json`, validation failure, or duplicate exclusion **SHALL**:
  - be recorded in `errors` with a stable code (`MISSING_MANIFEST`, `VALIDATION_FAILED`, `DUPLICATE_RUN_ID`, etc.),
  - set `ok` to `false` in the corresponding `runs` entry (if a manifest was partially readable) or omit from `runs` if no manifest existed,
  - increment `counts.invalid`.
- Summary generation **MUST NOT** throw or abort due to partial failures; the final summary is always produced for the ingested set.

## Out of Scope
- No new per-run artifact writes beyond the summary JSON (location to be defined in a future fragment).
- No metrics aggregation beyond counts/tallies defined above.
- No CLI exposure in IO.1.1.

## Determinism Guarantees
- Given identical `artifact_root` contents and identical access times, the summary JSON **MUST** be byte-for-byte deterministic (ordering + precedence rules + stable timestamps source controlled by caller).
