# EXECUTION_1.8 — Deterministic Failure, Retry, and Recovery Semantics

**Status:** Draft (spec-only, implementation pending)

## Scope
Defines deterministic failure classification, retry vs replay behavior, fan-out rules, recovery ordering, invariants, and non-goals for execution workflows. All behaviors are policy-versioned, immutable at runtime, and evaluated on the monotonic scheduler clock. No heuristics or best-effort logic are permitted.

## 1. Failure Taxonomy
- Every failure **MUST** map to exactly one class with stable criteria:
  - **Transient** vs **Terminal**: transient failures are conditionally retryable/replayable within policy bounds; terminal failures are permanently non-retryable.
  - **Retryable** vs **Non-retryable**: retryable failures **MUST** have fixed policy-defined caps; non-retryable failures **MUST NOT** be retried.
  - **Poisoned executions**: executions flagged by policy-defined predicates (e.g., repeated invariant violation, integrity breach) **MUST** be marked poisoned, are permanently terminal, and **MUST** short-circuit further retries/replays.
- Classification logic **MUST** be deterministic and stable across runs and releases; given identical inputs and failure signals, the same class **MUST** be selected.

## 2. Retry vs Replay Rules
- Retry caps **MUST** be fixed, versioned, and deterministic; no adaptive tuning.
- Replay eligibility **MUST** be explicitly defined (e.g., only idempotent stages or after checkpointed state); non-eligible executions **MUST NOT** be replayed.
- Idempotency enforcement:
  - Idempotent keys **MUST** be assigned to retries and replays to guarantee duplicate suppression.
  - Where exactly-once semantics are declared, retries/replays **MUST** present the same idempotent key and **MUST** be rejected if a prior completion exists.
  - Duplicate attempts **MUST** be suppressed deterministically using the idempotent key and policy-defined ordering.
- Retries vs replays **MUST** be distinguishable in lineage and logs (e.g., explicit attempt_type field).

## 3. Failure Fan-Out
- Propagation across regions, fault domains, and dependent executions/DAG edges **MUST** be explicit, deterministic, and bounded.
- Blast-radius accounting **MUST** define per-region and per-fault-domain limits; actions that would exceed limits **MUST** be denied with a deterministic “no-op with reason.”
- No implicit or cascading retries/replays without declared dependency linkage; undeclared dependencies **MUST** NOT be retried or replayed as a side effect.

## 4. Recovery Ordering
- Recovery precedence **MUST** be deterministic and policy-defined (e.g., by failure class → criticality → region/fault-domain → execution ID).
- Backoff windows **MUST** be fixed, versioned, and measured on the monotonic scheduler clock; no adaptive or randomized backoff.
- Recovery convergence **MUST** be explicitly defined (e.g., all dependent executions reached terminal or succeeded within policy windows). Terminal failure conditions **MUST** be enumerated and applied deterministically.

## 5. Invariants
- **MUST NOT** perform speculative retries.
- **MUST NOT** employ heuristic or probabilistic recovery logic.
- **MUST NOT** mutate retry/recovery policy at runtime; policy is versioned and immutable during execution.
- Same inputs + same failure sequence **MUST** yield the same outcome (including retry/replay decisions and terminal states).

## 6. Explicit Non-Goals
- No best-effort retries or recovery actions.
- No live state mutation during recovery beyond policy-defined idempotent actions.
- No ML-based, adaptive, or heuristic recovery decisions.
- No operator “nudging,” overrides, or hidden/manual changes to retry/recovery policy during execution.
