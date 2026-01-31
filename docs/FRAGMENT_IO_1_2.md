# FRAGMENT IO.1.2 — Aggregation Signing & Lineage (SPEC ONLY)

Status: FINAL (spec-only, LOCKED)  
Code: MUST NOT be implemented or modified without explicit approval.

## Scope
- Add a deterministic signing/lineage layer on top of IO.1.1 aggregation outputs.
- No new ingestion logic; strictly consumes IO.1.1 artifacts.
- No UI / CLI requirements in this fragment.

## Inputs
- IO.1.1 aggregation output JSON (authoritative, already validated).
- Source manifest index produced by IO.1.0/IO.1.1 (for lineage).
- Optional signing key material (path references only; never embed private keys).

## Outputs
- `aggregation_manifest.json`: canonical description of the aggregated set, including lineage.
- `aggregation_signature.json`: detached signature over `aggregation_manifest.json` payload bytes.
- No additional per-run files are created in IO.1.2.

## Invariants & Constraints
- MUST NOT mutate, reorder, or re-serialize upstream IO.1.1 outputs; consume them as-is.
- MUST include a deterministic `lineage` block listing all source run_ids and their artifact roots in stable lexical order.
- MUST include a `digest` object with algorithm name and hex digest of the exact IO.1.1 summary payload bytes.
- When duplicate run_ids are encountered across sources, the precedence rules from IO.1.1 MUST be preserved (later-precedence ordering retained; no re-dedup).
- Signing material MUST be referenced by path only; private key bytes MUST NOT appear in output.
- If any required input is missing or invalid, IO.1.2 MUST fail without emitting partial output files.

## Determinism
- All ordering (run_ids, paths, digest fields) MUST be lexical and stable across runs.
- The byte sequence used for signature MUST be the exact UTF-8 serialization of `aggregation_manifest.json` without reformatting.
- Given identical inputs and environment, outputs MUST be bit-for-bit identical.

## Error Handling
- Missing IO.1.1 summary or manifest index: hard fail, no outputs.
- Invalid or unreadable signing key path: hard fail, no outputs.
- Validation failure of upstream artifacts (as defined by IO.1.0/IO.1.1): hard fail, no outputs.
- Partial outputs are forbidden; either both `aggregation_manifest.json` and `aggregation_signature.json` are written, or none.
