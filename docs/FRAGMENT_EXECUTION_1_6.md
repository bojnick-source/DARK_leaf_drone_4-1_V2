# FRAGMENT EXECUTION_1.6 — Deterministic Capacity Forecasting & Autoscaling (FINAL & LOCKED)

## Scope
- Defines deterministic capacity forecasting inputs/invariants and autoscaling decision model.
- Specifies quota accounting (borrow/repay), cold vs warm pool lifecycle, scaling event lineage/auditability, and failure boundaries/non-goals.
- Excludes solver physics and non-execution UI.

## Inputs
- Historical and current execution workload metrics (arrival rates, runtime distributions, resource profiles) in fixed, non-overlapping windows/buckets with explicit rounding rules (ceil for arrivals, floor for runtimes).
- Forecast configuration (models, horizons, confidence bounds) with fixed seeds, immutable parameters, and versioned digests per release; no live tuning.
- Scheduler state from EXECUTION_1.0–1.5 with monotonic event ordering and last-applied policy digest (placements, preemptions, backpressure references, health/SLO status pointers).
- Quota ledgers per region/partition (allocations, borrow/repay rules, expirations) with monotonic sequence numbers.
- Pool definitions (cold/warm) including boot times, cost/latency tradeoffs, readiness probes, and deterministic readiness thresholds.

## Outputs
- Forecasted capacity requirements per region/partition and pool class with deterministic confidence intervals and explicit units.
- Autoscaling decisions (scale out/in per pool class) embedding thresholds/policies used and the stable ordering key applied.
- Quota adjustments (borrow/repay events) with deterministic ordering, idempotent event IDs, and effective-at timestamps on the scheduler monotonic clock.
- Pool lifecycle transitions (cold→warming→warm→drain→cold) with timestamps and reason codes, including the policy digest that authorized the transition.
- Scaling event lineage records capturing inputs, decisions, applied changes, resulting state, and the ordering key.

## Determinism & Decision Model
- Forecast computation MUST be deterministic given identical inputs: fixed feature windows, seeded models, and stable rounding/order of operations (round up to whole instances).
- Scale decisions MUST be a pure function of forecast outputs, current state, and declarative policy (no external time-varying randomness).
- Borrow/repay selection MUST be deterministic (closest-expiring debts → smallest principal → lexicographic region/partition).
- Cold vs warm pool selection MUST be deterministic: satisfy latency/SLO constraints first, then minimize cost, then prefer warm capacity before cold spin-up unless policy forbids.
- Scaling actions MUST include deterministic cool-down/hold-off windows on the scheduler monotonic clock; overlapping triggers MUST be resolved by timestamp → policy weight → region/partition ID → pool class.
- Any action with stale/missing required input MUST be rejected with a deterministic no-op record (including reason and ordering key) instead of partial execution.

## Quota Accounting (Borrow/Repay)
- Borrow events MUST record lender/borrower, amount, term, and repayment schedule; no implicit borrowing is allowed.
- Borrowing MUST respect per-region and global caps; attempted overages MUST be denied with reason codes and a no-op record.
- Repayment MUST be deterministic and prioritize overdue debts → soonest due → smallest principal → lexicographic region/partition; prepayment MUST update ledgers without side effects.
- Quota ledgers are append-only; corrections require compensating entries, not mutation.

## Cold vs Warm Pool Lifecycle
- Cold pool instances MUST be tracked through states: provisioned → booting → warming → warm → draining → deprovisioned, with monotonic timestamps per transition.
- Warm pools MUST be reused before creating new cold capacity when latency and SLO constraints are satisfied; determinism ties break by cost → age → pool ID.
- Draining MUST preserve in-flight work per EXECUTION_1.2 rollback/compensation rules; forced termination MUST be logged with fault-domain context.

## Scaling Lineage & Auditability
- Every forecast, decision, borrow/repay event, pool transition, and scaling action MUST emit a lineage record with inputs, policy digests, ordering keys, idempotent event IDs, and resulting state deltas.
- Lineage MUST be sufficient to replay and reproduce scaling outcomes with no hidden state; deterministic no-op outcomes MUST also be recorded.
- Failures in applying scaling actions MUST be captured with before/after state and compensating steps taken.

## Failure Boundaries & Non-Goals
- Scope excludes live state migration between regions/partitions and excludes speculative over-allocation beyond configured caps.
- Forecast/model drift detection is out-of-scope; only deterministic inputs/parameters are allowed.
- If external providers fail capacity requests, the system MUST degrade deterministically via backpressure/fairness rules from EXECUTION_1.4 and health/SLA rules from EXECUTION_1.5.
