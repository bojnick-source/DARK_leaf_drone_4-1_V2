# GOVERNANCE_1.0 — Spec Integrity and Change Control

## 1) Version Locking
- EXECUTION_1.x is LOCKED. Minor revisions MUST NOT change semantics, weaken invariants, or alter determinism guarantees. Any semantic change REQUIRES a new major execution version with explicit migration semantics.

## 2) Change Admission Rules
- Every proposed change MUST declare target version, affected fragments, and semantic impact classification (e.g., clarifying-only vs semantic). Proposals without explicit classification MUST be rejected. Governance decisions MUST be recorded before any fragment update.

## 3) Compatibility Guarantees
- All EXECUTION_1.x artifacts MUST remain replay-compatible, verification-compatible, and compliance-verifiable. Backward incompatibility within EXECUTION_1.x is FORBIDDEN. Policy/validation/observability/compliance artifacts MUST NOT introduce behaviors that violate prior EXECUTION_1.x replays.

## 4) Fragment Authority
- Fragment ownership is fixed: EXECUTION_* governs semantics; VALIDATION_* governs admissibility; OBSERVABILITY_* governs signals; COMPLIANCE_* governs proof; GOVERNANCE_* governs change control. Cross-fragment overrides are prohibited; conflicts MUST be rejected until resolved via explicit governance.

## 5) Enforcement Invariants
- No implicit spec extensions, undocumented behavior, runtime feature flags altering semantics, or emergency patches bypassing governance are permitted. All gating MUST be deterministic and policy-versioned.

## 6) Audit & Traceability
- Every accepted change MUST be logged, versioned, and causally linked to a governance approval record. Governance records MUST be immutable, replay-safe, and content-addressed. Absence or tampering of governance records constitutes a violation.

## 7) Invariants
- Governance decisions MUST be deterministic; identical proposals with identical evidence MUST yield identical outcomes. Governance processes MUST be auditable end-to-end and MUST NOT rely on human discretion beyond the declared rules.

## 8) Explicit Non-Goals
- No informal exceptions, hotfix semantics, trust-based approvals, heuristic review processes, or runtime policy mutation outside governed releases. No GOVERNANCE_1.1 (or higher) may be introduced without explicit approval under these rules.
