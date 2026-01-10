# FRAGMENT EXECUTION_1.6 — Deterministic Capacity Forecasting & Autoscaling (FINAL & LOCKED)

## Scope
- Defines deterministic capacity forecasting inputs/invariants and autoscaling decision model.
- Specifies quota accounting (borrow/repay), cold vs warm pool lifecycle, scaling event lineage/auditability, and failure boundaries/non-goals.
- Excludes solver physics and non-execution UI.

## Inputs
- Historical and current execution workload metrics (arrival rates, runtime distributions, resource profiles) with deterministic windows/buckets.
- Forecast configuration (models, horizons, confidence bounds) with fixed seeds and immutable parameters.
- Scheduler state from EXECUTION_1.0–1.5 (placements, preemptions, backpressure, health/SLO status, fairness).
- Quota ledgers per region/partition (allocations, borrow/repay rules, expirations).
- Pool definitions (cold/warm) including boot times, cost/latency tradeoffs, and readiness probes.

## Outputs
- Forecasted capacity requirements per region/partition and pool class with deterministic confidence tiers.
- Autoscaling decisions (scale out/in per pool class) with ordered rationale and thresholds used.
- Quota adjustments (borrow/repay events) with deterministic ordering and repayment schedule.
- Pool lifecycle transitions (cold→warming→warm→drain→cold) with timestamps and reason codes.
- Scaling event lineage records capturing inputs, decisions, applied changes, and resulting state.

## Determinism & Decision Model
- Forecast computation MUST be deterministic given identical inputs: fixed feature windows, seeded models, and stable rounding/order of operations.
- Scale decisions MUST be a pure function of forecast outputs, current state, and declarative policy (no external time-varying randomness).
- Borrow/repay selection MUST be deterministic (prioritize closest-expiring debts, then smallest principal, then lexicographic region/partition).
- Cold vs warm pool selection MUST be deterministic: satisfy latency/SLO constraints first, then minimize cost, then prefer warm capacity before cold spin-up unless policy forbids.
- Scaling actions MUST include deterministic cool-down/hold-off windows; overlapping triggers MUST be resolved by timestamp then policy weight then region/partition ID.

## Quota Accounting (Borrow/Repay)
- Borrow events MUST record lender/borrower, amount, term, and repayment schedule; no implicit borrowing is allowed.
- Repayment MUST be deterministic and prioritize overdue debts; prepayment MUST update ledgers without side effects.
- Borrowing MUST respect per-region and global caps; denials MUST be logged with reason codes.
- Quota ledgers are append-only; corrections require compensating entries, not mutation.

## Cold vs Warm Pool Lifecycle
- Cold pool instances MUST be tracked through states: provisioned → booting → warming → warm → draining → deprovisioned.
- Warm pools MUST be reused before creating new cold capacity when latency and SLO constraints are satisfied.
- Draining MUST preserve in-flight work per EXECUTION_1.2 rollback/compensation rules; forced termination MUST be logged with fault-domain context.

## Scaling Lineage & Auditability
- Every forecast, decision, borrow/repay event, pool transition, and scaling action MUST emit a lineage record with inputs, policy digests, ordering keys, and resulting state deltas.
- Lineage MUST be sufficient to replay and reproduce scaling outcomes with no hidden state.
- Failures in applying scaling actions MUST be captured with before/after state and compensating steps taken.

## Failure Boundaries & Non-Goals
- Scope excludes live state migration between regions/partitions and excludes speculative over-allocation beyond configured caps.
- Forecast/model drift detection is out-of-scope; only deterministic inputs/parameters are allowed.
- If external providers fail capacity requests, the system MUST degrade deterministically via backpressure/fairness rules from EXECUTION_1.4 and health/SLA rules from EXECUTION_1.5.
