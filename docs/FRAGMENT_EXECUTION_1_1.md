# FRAGMENT EXECUTION_1.1 — Orchestration Refinements (SPEC ONLY, DRAFT)

## Scope
- Extends EXECUTION_1.0 to cover batched/partitioned orchestration, multi-phase scheduling (stage → run → postprocess), and lineage to prior IO.1.x/IO.2.0 artifacts.
- Adds explicit contracts for partial-ledger emission, deterministic resumption, and deduplication across repeated invocations.
- Excludes solver physics, engine internals, transport protocols, and UI controls.

## Inputs
- A validated EXECUTION_1.0 execution plan (execution_id, ordered run_ids, config).
- Optional partitions: disjoint subsets of run_ids with partition_id (deterministic hash).
- Optional postprocess hooks referencing IO.1.x/IO.2.0 artifacts to materialize after run completion.
- Idempotency token (caller supplied) for deduplication of externally visible side effects.

## Outputs
- Partition-aware execution ledger:
  - execution_id (unchanged from EXECUTION_1.0) and partition_id (if present).
  - ordered run entries with lifecycle traces extended by partition context.
  - postprocess outcomes per run (succeeded/failed/skipped) with timestamps.
- Resumption cursor:
  - opaque, deterministic cursor encoding last fully emitted record per partition.
- Deterministic dedup report:
  - list of run_ids suppressed due to idempotency token or duplicate partition replay.

## Lifecycle & Phases
- States extend EXECUTION_1.0 with:
  - postprocess_pending → postprocessing → (postprocess_succeeded | postprocess_failed)
  - resumable_halt (non-terminal pause point; only allowed between partitions or after postprocess_pending)
- Partition execution flow:
  - pending → staging → running → terminal (succeeded/failed/timed_out/canceled) → postprocess_pending → postprocessing → postprocess_terminal (succeeded/failed)
- Resumption:
  - resumable_halt may transition back to staging/running/postprocessing based on cursor.
  - No state rewinds within a run_id; only forward progress.

## Determinism & Ordering
- Partition ordering MUST be deterministic: sort partitions by partition_id; within a partition, stable sort by run_id then prior insertion order.
- Resumption cursor MUST be a deterministic, content-addressed digest over emitted records up to the cursor boundary.
- Replays with identical execution_id, partition_id, and idempotency token MUST emit byte-for-byte identical ledgers (including dedup reports).
- Postprocess hooks MUST execute in deterministic order per run_id (stable topological order if dependencies declared, otherwise run_id order).

## Invariants
- execution_id, partition_id, and idempotency token are immutable for a given invocation.
- A run_id MUST NOT appear in more than one partition; violation is a validation error.
- Ledgers MUST be append-only; previously emitted records are never rewritten.
- Timestamps MUST be RFC3339 UTC and strictly non-decreasing per run_id across all phases (including postprocess).
- Postprocess failure MUST NOT erase or downgrade a succeeded run outcome; it records an additional postprocess_failed terminal.
- Deduplication MUST NOT drop error records; only duplicate successes are suppressed.

## Error Handling
- Partition validation failures abort that partition before staging; other partitions may proceed only if the caller opts-in (flag required).
- Resumption with stale or mismatched cursor MUST be rejected with a deterministic error code.
- Postprocess hook errors MUST be labeled with hook_id and propagated to the ledger.
- If dedup detects conflicting outcomes for the same execution_id + idempotency token, the orchestration MUST fail the invocation with a conflict error.

## Traceability (informational, non-normative)
- Ledgers SHOULD reference source manifest digests (IO.1.x) and publication manifest digests (IO.2.0) when postprocessing consumes or publishes artifacts.
- Resumption cursor SHOULD be logged alongside execution_id for audit replay.
