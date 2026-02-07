# EXECUTION_1.10 — Deterministic Time, Deadlines, and Timeouts

## Time Model
- The scheduler’s single monotonic clock SHALL be the sole source of time; wall-clock, locale, and system time MUST NOT be used.
- Time SHALL advance only via ordered scheduler events; clock state (current value, event ordering) MUST be present in replay inputs.
- All time quantities (deadlines, timeouts, windows) SHALL be expressed in scheduler-clock units and MUST be versioned with the policy that defines them.

## Deadlines
- Deadlines SHALL be absolute values on the scheduler clock and evaluated only at deterministic checkpoints defined by policy.
- A deadline miss SHALL be a terminal, ordered outcome that preempts retries, replays, or recovery once recorded.
- Deadline policies (values, checkpoints, precedence) MUST be versioned and immutable at runtime.

## Timeouts
- Timeout windows MUST be deterministic, versioned, and defined per execution phase with explicit start/end points on the scheduler clock.
- Sliding, adaptive, or heuristic timeout extensions are prohibited; timeout expiration SHALL emit a terminal, ordered reason code.
- Timeout definitions MUST be replayable from inputs (policy version, start trigger, duration).

## Ordering & Precedence
- Ordering among deadline expiry, timeout expiry, cancellation, and failure recovery SHALL be deterministic: timestamp → policy weight → ordering key (region/partition/run) → stable tie-breaks defined in policy.
- Identical inputs and event order MUST yield identical outcomes; once a terminal deadline/timeout is recorded, subsequent retries/replays/recovery MAY NOT proceed unless explicitly allowed by policy (e.g., marked as soft-timeout with declared follow-on rule).

## Fan-Out & Propagation
- Propagation of deadline/timeout expiry across dependent executions, regions, and fault domains MUST follow declared DAG edges and policy-defined blast-radius bounds; no implicit cascading is allowed.
- Blast-radius accounting for time-based termination SHALL be explicit, per edge/region/fault-domain, and enforced before propagation.

## Invariants
- Time-based decisions MUST be replayable and monotonic; no speculative early termination or best-effort grace periods are permitted.
- Runtime mutation of deadlines, timeouts, or related policy is forbidden; policy changes MUST occur via versioned updates and take effect only on new evaluations.
- Same inputs + same event order MUST produce identical deadline/timeout outcomes.

## Observability & Audit
- Every deadline/timeout event SHALL record: triggering clock value, configured threshold/window, policy/version, ordering key (e.g., region/partition/run), and terminal reason code.
- Logs and lineage MUST allow exact temporal reconstruction for replay and audit.

## Explicit Non-Goals
- No wall-clock or real-time guarantees.
- No adaptive or ML-based time adjustments.
- No operator “grace” overrides or hidden extensions.
- No implicit time dilation/acceleration; only the monotonic scheduler clock is authoritative.
