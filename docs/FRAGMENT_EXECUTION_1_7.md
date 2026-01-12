# FRAGMENT EXECUTION_1.7 — Multi-Region & Fault-Domain Execution (SPEC ONLY, DRAFT)

## Scope
- Extends EXECUTION_1.x with deterministic multi-region and fault-domain semantics.
- Covers deterministic region selection/pinning, fault-domain isolation and blast-radius guarantees, cross-region replay and convergence, region-level quota partitioning and spillover, and global vs regional scheduling invariants.
- Explicitly excludes live state migration or runtime policy retuning.

## Inputs
- Region topology and fault-domain definitions (failure domains, isolation groups, blast-radius budgets).
- Region-level quotas/allocations and spillover policies (caps, priorities, eligibility).
- Scheduler state from EXECUTION_1.0–1.6 (placements, preemptions, backpressure, health/SLA outcomes).
- Cross-region replication/replay policies (consistency level, convergence windows).
- Deterministic region selection rules (pinning constraints, anti-affinity, locality hints).

## Outputs
- Region selection and pinning decisions with ordered reason codes.
- Placement plans annotated with fault-domain lineage and blast-radius accounting.
- Spillover/borrow events between regions with deterministic ordering and repayment terms.
- Cross-region replay and convergence actions with deterministic scopes and timelines.
- Global and per-region scheduling ledgers showing quota usage, isolation status, and any rejected actions.

## Determinism & Decision Rules
- Region selection MUST be deterministic given the same topology, quotas, pinning/affinity inputs, and scheduler state; ties resolve by timestamp → policy weight → region_id → fault-domain_id → run_id.
- Blast-radius accounting MUST be performed before admission; if budgets would be exceeded, the action MUST be rejected with a deterministic reason and ordering key.
- Spillover/borrow eligibility MUST be evaluated deterministically; borrow caps and priorities are applied before placement, and any denial is recorded as a no-op with reason.
- Replay/convergence actions MUST run on fixed, deterministic windows (monotonic scheduler clock) and use stable ordering keys; conflicting actions resolve by timestamp → policy weight → source region_id → target region_id.
- Cross-region consistency level (e.g., at-least-once, exactly-once-with-idempotent-keys) MUST be declared and enforced deterministically across runs.

## Invariants
- Region and fault-domain isolation budgets MUST never be exceeded; attempted overages MUST be denied with explicit codes.
- Spillover/borrow balances MUST remain within configured regional and global caps; repayments follow deterministic ordering (overdue → soonest due → smallest principal → lexicographic region_id).
- Replay/convergence actions MUST be idempotent and attributable to specific input digests; no hidden state.
- Scheduling decisions MUST preserve ordering and fairness guarantees from EXECUTION_1.3–1.6; multi-region logic MUST NOT weaken prior determinism or backpressure invariants.
- All outputs MUST include policy digests (thresholds, weights, ordering keys) sufficient for deterministic replay.

## Audit & Traceability
- Log every region selection, pinning decision, spillover/borrow, replay/convergence action, denial, and repayment with timestamps, ordering keys, involved region/fault-domain IDs, quotas, budgets, and policy digests.
- Logs MUST permit deterministic reconstruction of multi-region scheduling, isolation, and convergence outcomes.
