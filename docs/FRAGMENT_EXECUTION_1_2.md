# FRAGMENT EXECUTION_1.2 — Failure Recovery & Replay (SPEC ONLY, FINAL & LOCKED)

## Scope
- Extends EXECUTION_1.x to define deterministic recovery, replay, and compensation semantics.
- Covers checkpoints, idempotent replay, retry/backoff policy, rollback/compensation ordering, partial-run error propagation, and audit logging requirements.
- Excludes solver physics, transport details, and any UI/UX concerns.

## Inputs
- A validated execution ledger from EXECUTION_1.0/1.1 (execution_id, run timelines, partitions if any).
- Recovery policy:
  - checkpoint cadence (per run or per phase)
  - retry/backoff configuration (max_attempts, base/backoff strategy, retryable labels)
  - compensation handlers (optional) with declared ordering constraints.
- Idempotency scope token to bind replayed effects.
- Optional replay window selector (run_id subset, partition_id subset, or cursor).

## Outputs
- Recovery ledger extensions (append-only):
  - checkpoint records with deterministic offsets and content hashes.
  - replay traces per run_id including attempt numbers, retry reasons, and backoff applied.
  - compensation records (if invoked) with handler_id and outcome.
  - propagated partial-run error summaries referencing original failures.
- Updated deterministic resumption cursor encoding highest durable checkpoint + emitted recovery records.

## Lifecycle & Recovery States
- Adds recovery_pending → recovering → (recovered | recovery_failed) per run_id.
- Checkpoint emission points:
  - after staging, after running, after postprocess (if defined), and before compensation.
- Replay:
  - recovering re-enters staging/running only for retryable failures and within max_attempts.
  - recovery_failed is terminal and MUST preserve prior failure context.
- Compensation:
  - triggered only when configured and after recovery_failed or explicit rollback request.
  - compensation handlers run in declared stable order; failures are recorded but do not erase prior ledger history.

## Determinism & Ordering
- Checkpoint identifiers MUST be deterministic hashes over run_id, phase, sequence, and prior cursor.
- Replay order MUST be stable: sort by run_id, then by original failure timestamp, then attempt number.
- Backoff schedule MUST be deterministic given the retry policy (e.g., fixed or deterministic exponential with jitter = 0).
- Compensation ordering MUST be deterministic and reproducible; no concurrent compensation for the same run_id.
- Replays with identical execution_id + idempotency scope MUST emit byte-for-byte identical recovery ledgers.

## Invariants
- Ledgers remain append-only; recovery/replay/compensation never mutate prior records.
- A checkpoint MUST uniquely map to a single run_id + phase + sequence; duplicates are an error.
- Partial-run errors MUST propagate forward; retries cannot drop or rewrite failure context.
- Retry attempts MUST increment attempt_number monotonically starting at 1.
- Backoff MUST honor configured bounds; exceeding max_attempts transitions to recovery_failed.
- Compensation handlers MUST be idempotent and MUST NOT reintroduce side effects already recorded as succeeded.

## Replay & Retry Rules
- Only failures labeled retryable by policy may be replayed; non-retryable failures go directly to recovery_failed.
- If a replay reaches succeeded, prior failure records remain but a final recovered record is appended.
- Idempotent replay MUST suppress duplicate external side effects using the idempotency scope token.
- Stale or mismatched resumption cursors MUST be rejected with a deterministic error code.

## Error Handling
- Missing or corrupt checkpoints MUST fail recovery for the affected run_id with a checkpoint_corrupt label.
- Backoff policy misconfiguration MUST reject the invocation before any replay starts.
- Compensation handler failures MUST be recorded with handler_id and reason; recovery outcome remains recovery_failed.

## Audit Logging (MUST)
- Log every checkpoint emission, replay attempt, backoff application, and compensation invocation with execution_id, run_id, attempt_number, and cursor.
- Logs MUST be ordered identically to ledger emission to allow deterministic reconstruction.
- Audit logs MUST include the idempotency scope token and recovery policy digest for traceability.
