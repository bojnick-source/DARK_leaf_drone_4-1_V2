# FRAGMENT EXECUTION_1.4 — Cross-Workflow Coordination & Backpressure (SPEC ONLY, FINAL, LOCKED)

## Scope
- Extends EXECUTION_1.x with deterministic cross-workflow coordination, global fairness across schedulers, starvation avoidance guarantees, and deterministic backpressure signaling.
- Governs coordination between multiple execution schedulers/queues handling shared resources and shared fairness domains.
- Excludes solver physics, transport details, and UI/UX.

## Inputs
- Execution ledger from EXECUTION_1.0–1.3 (execution_id, runs, partitions, placements, preemption history).
- Scheduler topology:
  - set of schedulers participating in a shared fairness domain.
  - coordination channel semantics (ordering, durability) with deterministic tie-breakers.
- Fairness policy parameters (global weights/priority classes, aging/boost rules) applied across schedulers.
- Backpressure thresholds (queue depth, latency/SLA breach signals, resource saturation signals).
- Admission/backpressure policies per scheduler (max in-flight, burst limits, rejection/defer rules).

## Outputs
- Coordinated admission decisions per scheduler with deterministic global ordering keys.
- Global fairness ledger entries (append-only) reflecting credit/debit across schedulers.
- Backpressure signals (assert/clear) with deterministic causes and scope (per scheduler and global).
- Starvation-avoidance actions (priority boosts or protected slots) with deterministic activation/deactivation.

## Coordination & Fairness Rules
- Schedulers in the same fairness domain MUST apply a shared ordering key: priority weight (desc), fairness credit/deficit, then run_id lexicographic.
- Cross-scheduler coordination MUST be repeatable: identical inputs yield identical admission sequences and placement lineage choices.
- Fairness credits/debits MUST be computed deterministically and logged; no implicit state is allowed.
- Protected slots for starvation avoidance MUST be limited and allocated deterministically (stable run_id ordering).

## Backpressure & Starvation Avoidance
- Backpressure assertions MUST trigger deterministic actions: pause new admissions beyond configured burst, optionally demote/slow specific priority bands.
- Backpressure clear MUST be deterministic and monotonic: only when all triggering thresholds are below hysteresis floors.
- Starvation detection MUST be deterministic (e.g., maximum wait time or credit deficit threshold) and MUST NOT violate global fairness constraints.
- When starvation protection is active, fairness accounting MUST record the exception and compensation to restore fairness after relief.

## Determinism & Ordering
- Coordination channels MUST preserve total ordering per fairness domain; ties resolved by scheduler_id then run_id.
- Placement selection under coordination MUST reuse EXECUTION_1.3 deterministic placement lineage; no divergence allowed.
- Backpressure and starvation events MUST be reproducible from ledgers and inputs without hidden state.

## Invariants
- Ledgers (admission, fairness, backpressure) are append-only; no mutation of historical entries.
- No scheduler may exceed configured global quotas; violations MUST be prevented via deterministic deferral/rejection.
- Starvation protection MUST NOT erase prior audit context or placement lineage.
- Backpressure signals MUST align with ledger order to enable deterministic replay.

## Audit & Traceability
- Every coordinated admission, fairness credit/debit, backpressure assert/clear, and starvation protection activation/deactivation MUST be logged with execution_id, run_id (if applicable), scheduler_id, ordering key, and reason code.
- Audit logs MUST include policy digests (fairness parameters, backpressure thresholds, starvation rules) to enable deterministic reconstruction.
