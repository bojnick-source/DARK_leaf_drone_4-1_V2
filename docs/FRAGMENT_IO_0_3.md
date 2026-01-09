# FRAGMENT IO.0.3 — Run Artifact Writer (Authoritative Spec)

## Scope
- IO only: file/directory materialization for a completed run.
- No physics/solvers/CLI changes.
- Affects only `v2/engine/include/v2/io/`, `v2/engine/src/io/` (if needed for implementations), `v2/engine/tests/`, and `schemas/`.

## Deterministic Artifact Root
All run artifacts live under the repository-root–relative prefix:

```
artifacts/
  runs/
    <run_id>/
```

Where `<run_id>` is the 16-character lowercase hex string produced by the canonical input hashing helpers (`run_id_from_inputs`) and **must match** the `run_id` field in the output payload.

## Required Files (per run_id)

### 1) `artifacts/runs/<run_id>/run_output.json`
* **Schema**: must conform to `schemas/run_output.schema.json`.
* **Content** (mirrors schema fields):
  - `run_id` (string): the same 16-character lowercase hex string as the directory name.
  - `ok` (boolean): true if the run succeeded.
  - `label` (string|null): failure label when `ok == false`; must be `null` when `ok == true`. Allowed labels are the `FailLabel` enum values.
  - `inputs` (object): normalized input map used to derive `run_id` (canonicalized ordering/formatting per IO.0.2).
  - `metrics` (object): numeric scalar metrics; each value is a JSON number.
  - `artifacts` (object, optional):
    - `root` (string): the absolute or repo-relative base path for this run’s artifacts; conventionally `artifacts/runs/<run_id>`.
    - `paths` (array of strings): relative artifact file paths (from `root`) that were emitted for the run (e.g., additional data files). Use an empty array when no extra files exist.

### 2) Additional artifact payloads (optional)
* Any extra per-run files (plots, CSVs, etc.) should be written **inside** `artifacts/runs/<run_id>/`.
* Every such file path must be listed in `run_output.json.artifacts.paths` relative to `artifacts/runs/<run_id>`.

## Overwrite/Idempotency Rules
* Writers must create parent directories as needed.
* Writing the same run_id multiple times overwrites existing files atomically (replace-on-write) to keep the layout deterministic.

## Serialization Requirements
* JSON output must be deterministic: stable key ordering and stable float formatting consistent with IO.0.2 canonicalization.
* Use UTF-8 encoding with trailing newline permitted.

