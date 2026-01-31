# FRAGMENT EXECUTION_1.0 — Execution Orchestration (SPEC ONLY, DRAFT)

## Scope
- Defines the orchestration contract for running v2 computational jobs that consume IO.1.x ingest/aggregation outputs and produce IO.0.x/IO.1.x artifacts.
- Covers scheduling, lifecycle states, transition rules, determinism guarantees, failure handling, and externally visible inputs/outputs.
- Excludes solver physics, engine internals, studio UI, and any transport-specific plumbing (REST/gRPC/message bus details are out of scope).

## Inputs
- A set of validated run manifests (IO.0.4 run_output) or aggregated indices (IO.1.1/IO.1.2) referenced by canonical run_id.
- Execution configuration:
  - target engine version/commit (immutable identifier)
  - resource profile (CPU/GPU/memory constraints, queue/class)
  - max concurrency (MUST be explicit; default forbidden)
  - retry policy (bounded attempts, backoff, and retryable failure labels)
  - timeouts (wall-clock and per-task)
  - required artifacts to stage (paths under artifacts/runs/<run_id>/)
- Optional filters: subset of run_ids, labels, or tags to include.

## Outputs
- An execution ledger per orchestration invocation:
  - immutable execution_id (deterministic hash of ordered inputs + config)
  - ordered list of scheduled run_ids with resolved engine version and resource profile
  - lifecycle trace for each run_id (state timeline with timestamps in RFC3339 UTC)
  - outcome summary (pass/fail/cancel/timeout) with failure labels where applicable
  - deterministic ordering of emitted records (lexicographic by run_id, then state timestamp)
- Optional aggregate summary:
  - counts per outcome (pass/fail/cancel/timeout)
  - failure label tallies
  - retry statistics (attempts, succeeded_on_retry)

## Lifecycle States
- pending → staging → running → (succeeded | failed | canceled | timed_out)
- Transient states:
  - staging: artifacts/materialization in progress
  - retry_wait: bounded backoff before re-entering staging or running
- Terminal states: succeeded, failed, canceled, timed_out
- State transition rules:
  - pending → staging MUST occur only after inputs are validated and resources reserved.
  - staging → running MUST occur only after required artifacts are present and integrity-checked.
  - running → succeeded requires all mandated outputs produced and validated.
  - running → failed requires at least one failure label from the allowed set.
  - running → timed_out only via configured timeout expiry.
  - Any terminal state is immutable; no further transitions allowed.

## Determinism & Ordering
- The execution_id SHALL be a deterministic hash over:
  - sorted run_ids
  - normalized execution configuration (engine version, resource profile, retry/timeout values)
  - optional filters (sorted)
- Scheduling order MUST be deterministic: stable sort by run_id, then insertion order for ties.
- Ledger emission MUST be stable and reproducible given identical inputs/config.
- Retries MUST not reorder unrelated runs; only the retrying run’s state timeline extends.

## Invariants
- Inputs MUST be validated (IO.0.4/IO.1.1/IO.1.2) before scheduling.
- A run_id MUST appear at most once in the scheduled set; duplicates are rejected.
- Engine version is immutable per execution_id.
- Resource profile and timeouts are immutable per execution_id.
- Every lifecycle record MUST include monotonic timestamps (RFC3339 UTC) and non-decreasing sequence numbers per run_id.
- Failure labels MUST come from the authoritative FailLabel set.
- Timeouts and retries MUST respect configured bounds; no unbounded retries.

## Error Handling
- Validation failures abort the execution before scheduling (no ledger emission except a top-level error).
- Artifact staging errors MUST transition the run to failed with a staging_error label.
- Timeouts MUST record timed_out with the configured timeout value.
- Cancellations MUST be explicit, recorded with actor and reason.
- Partial progress MUST still emit deterministic ledger entries for completed runs.

## Logging & Traceability (informational, non-normative)
- Execution_id and run_id SHOULD be included in all logs/metrics for correlation.
- Ledger SHOULD reference source manifest hashes to link back to IO.1.x artifacts.
