# FRAGMENT EXECUTION_1.3 — Resource-Aware Scheduling & Admission (SPEC ONLY)

## Scope
- Extends EXECUTION_1.x with deterministic resource-aware scheduling, admission control (quotas, priority, fairness), placement lineage, and preemption policy.
- Governs how executions are enqueued, placed, paused/preempted, and resumed under resource pressure.
- Excludes solver physics, transport details, and UI/UX.

## Inputs
- Execution ledger from EXECUTION_1.0–1.2 (execution_id, runs, partitions, states).
- Resource model:
  - capacity by resource class (e.g., CPU, GPU, mem, IO) and per-partition quotas.
  - scheduling weights/priority classes with optional aging parameters.
  - fairness policy (e.g., weighted fair share) and preemption policy (grace/eviction rules).
- Placement constraints (affinity/anti-affinity, zone/host filters) and deterministic tie-breakers.
- Admission queue policy (batch size, max in-flight, queue ordering).

## Outputs
- Admission decisions (accepted, deferred, rejected) with deterministic reasons.
- Placement plan per admitted run: selected resource class, partition/host, and placement lineage ID.
- Preemption records (who, why, when, grace) and resumptions (if allowed).
- Updated scheduling ledger entries (append-only) reflecting queue state transitions.

## Scheduling & Admission Rules
- Admission MUST honor capacity and quotas first, then priority/weight, then deterministic tie-breakers (run_id lexicographic).
- Fairness MUST be enforced per configured policy and MUST be repeatable under identical inputs.
- Placement lineage ID MUST be a deterministic hash over execution_id, run_id, resource class, partition, and placement attempt index.
- Rejected admissions MUST NOT mutate prior ledger; deferrals remain queued with stable ordering keys.

## Preemption & Resumption
- Preemption triggers: quota reclaim, higher-priority admission, or explicit administrative action.
- Preemption MUST record grace windows; if grace expires, eviction is deterministic and logged.
- Resumptions MUST reuse the prior placement lineage where constraints allow; otherwise a new lineage is emitted with a parent pointer to the evicted lineage.
- Preempted runs return to the admission queue at the same priority with deterministic tie-breaker ordering.

## Determinism & Ordering
- Queue ordering: sort by priority weight (desc), then fairness key, then run_id lexicographic.
- When priorities tie, aging adjustments MUST be deterministic and monotonic.
- Placement selection within a resource class MUST be deterministic: stable sort over eligible hosts by host_id and residual capacity hash.
- Identical inputs MUST yield identical admission, placement, and preemption decisions byte-for-byte.

## Invariants
- Ledgers remain append-only; no mutation of historical admissions or placements.
- Quota violations MUST never be emitted; decisions that would violate quotas are deferred or rejected deterministically.
- A run_id MAY have multiple placement lineage records only via preemption/resumption; each lineage ID is unique.
- Preemption MUST NOT drop previously recorded failure or recovery context.

## Audit & Lineage Requirements
- Every admission, deferral, rejection, placement, preemption, and resumption MUST be logged with execution_id, run_id, decision reason, and lineage ID (if any).
- Audit logs MUST align in order with scheduling ledger emission for deterministic replay.
- Resource policy digests (capacity, quotas, fairness, preemption) MUST be included in audit entries for traceability.

