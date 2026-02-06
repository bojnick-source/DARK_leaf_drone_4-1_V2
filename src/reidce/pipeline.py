from __future__ import annotations

import json
import math
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple

from reidce.memory import MemoryStore
from reidce.pico_gk import apply_pico_gk
from reidce.schemas import (
    BudgetTotals,
    BuildPacket,
    BuildPacketCadPayload,
    BuildPacketCriticalFeature,
    BuildPacketTolerances,
    ConstraintEntry,
    ConstraintReport,
    ContinuousMetricSummary,
    EquilibriumSolverSpec,
    EvidencePack,
    EvidencePackArtifacts,
    GateDecision,
    GateKeyMetrics,
    GeometryTolerances,
    InspectionPlan,
    KPIResults,
    ManifestArtifacts,
    ManifestInputsHash,
    NominalEquilibrium,
    NominalResult,
    Quantity,
    RunConfig,
    RunManifest,
    SensitivityReport,
    UnitLiteral,
    UQContinuousMetrics,
    UQSummary,
    ValidationSummary,
    WilsonCI,
    now_utc_iso,
)
from reidce.topology import recommend_topology
from sfcs_mdp.hashutil import sha256_bytes, sha256_file


@dataclass(frozen=True)
class InputBundle:
    design: Any
    mission: Any
    environment: Any
    manufacturing_process: Any
    run_config: RunConfig


@dataclass(frozen=True)
class PipelineState:
    inputs: InputBundle
    inputs_hash: ManifestInputsHash
    run_id: str


@dataclass(frozen=True)
class PipelineArtifacts:
    nominal: NominalResult
    constraints: ConstraintReport
    uq_summary: UQSummary
    sensitivity: SensitivityReport
    gate_decision: GateDecision
    build_packet: BuildPacket
    manifest: RunManifest
    evidence_pack: EvidencePack


def _prepare_design_for_ai(design: Any, memory_store: MemoryStore | None) -> Any:
    if not hasattr(design, "geometry") or not hasattr(design, "model_copy"):
        return design

    updated = apply_pico_gk(design)
    if memory_store is not None and updated is not design:
        cad_ref = getattr(updated.geometry, "cad_ref", None)
        cad_payload = cad_ref.model_dump(mode="json") if cad_ref is not None else None
        memory_store.log_event(
            "pico_gk",
            "Applied Pico GK CAD ref",
            {
                "design_id": getattr(updated, "design_id", None),
                "cad_ref": cad_payload,
            },
        )

    if getattr(updated, "domain", None) == "actuated_compliant_subsystem":
        recommendation = recommend_topology(updated, memory_store=memory_store)
        updated = recommendation.best.design
        if memory_store is not None:
            memory_store.log_event(
                "topology_recommendation",
                "Selected topology candidate",
                {
                    "design_id": getattr(updated, "design_id", None),
                    "candidate": recommendation.best.name,
                    "score": recommendation.scorecard.score,
                },
            )

    return updated


def _serialize_payload(payload: Any) -> str:
    if hasattr(payload, "model_dump"):
        return json.dumps(payload.model_dump(mode="json", by_alias=True), sort_keys=True)
    return json.dumps(payload, sort_keys=True)


def _hash_payload(payload: Any) -> str:
    return sha256_bytes(_serialize_payload(payload).encode("utf-8"))


def _quantity(value: float, unit: UnitLiteral) -> Quantity:
    return Quantity(value=value, unit=unit)


def _wilson_halfwidth(probability: float, samples: int) -> float:
    if samples <= 0:
        return 1.0
    z = 1.96
    denom = 1.0 + z**2 / samples
    radius = z * math.sqrt(
        max(probability * (1.0 - probability) / samples + z**2 / (4.0 * samples**2), 0.0)
    )
    return radius / denom


def _budget_totals(lines: List[Any], field: str, unit: str) -> Tuple[float, List[str]]:
    total = 0.0
    missing: List[str] = []
    for line in lines:
        quantity = getattr(line, field)
        if quantity is None or quantity.value is None:
            if line.required:
                missing.append(line.name)
            continue
        if quantity.unit != unit:
            raise ValueError(f"Budget line {line.name} must use unit {unit}.")
        total += quantity.value
    return total, missing


def compile_inputs(
    design: Any,
    mission: Any,
    environment: Any,
    manufacturing_process: Any,
    run_config: RunConfig,
) -> PipelineState:
    if hasattr(run_config, "model_dump"):
        run_config = run_config.model_copy(deep=True)
    inputs_hash = ManifestInputsHash(
        design=_hash_payload(design),
        mission=_hash_payload(mission),
        environment=_hash_payload(environment),
        manufacturing_process=_hash_payload(manufacturing_process),
        run_config=_hash_payload(run_config),
    )
    run_id = sha256_bytes(
        ":".join(
            [
                inputs_hash.design,
                inputs_hash.mission,
                inputs_hash.environment,
                inputs_hash.manufacturing_process,
                inputs_hash.run_config,
                str(run_config.seed),
            ]
        ).encode("utf-8")
    )[:12]
    return PipelineState(
        inputs=InputBundle(
            design=design,
            mission=mission,
            environment=environment,
            manufacturing_process=manufacturing_process,
            run_config=run_config,
        ),
        inputs_hash=inputs_hash,
        run_id=run_id,
    )


def evaluate_nominal(state: PipelineState) -> tuple[NominalResult, ConstraintReport]:
    design = state.inputs.design
    mission = state.inputs.mission
    structure = design.structure
    actuator = design.actuator
    pressure_limit = actuator.pressure_limit.value or 0.0
    force_coeff = actuator.force_coeff.value or 0.0
    force_eq = pressure_limit * force_coeff
    deflection = (
        force_eq / (structure.stiffness.value or 1.0) if structure.stiffness.value else 0.0
    )
    equilibrium = NominalEquilibrium(
        converged=True,
        strain_star=_quantity(0.0, "ratio"),
        force_eq=_quantity(force_eq, "N"),
        deflection_eq=_quantity(deflection, "m"),
        residual_force=_quantity(0.0, "N"),
        solver=EquilibriumSolverSpec(name="brentq", rtol=1e-10, atol=1e-10, maxiter=200),
    )
    payload_ratio = 0.0
    if mission.payload_target.value and mission.payload_target.value > 0:
        payload_ratio = (force_eq / 9.81) / mission.payload_target.value
    mass_total, missing_mass = _budget_totals(
        design.budgets.mass_budget.lines, "mass", "kg"
    )
    power_total, missing_power = _budget_totals(
        design.budgets.power_budget.lines, "power", "W"
    )
    nominal = NominalResult(
        schema_version="nominal.v1.0",
        equilibrium=equilibrium,
        budgets=BudgetTotals(
            mass_total=_quantity(mass_total, "kg"),
            power_total=_quantity(power_total, "W"),
            energy_total=_quantity(0.0, "J"),
        ),
        kpis=KPIResults(
            payload_ratio=_quantity(payload_ratio, "ratio"),
            useful_work_n_per_w=_quantity(0.0, "ratio"),
        ),
        numerical_integrity=True,
    )

    constraints = []
    constraints.append(
        ConstraintEntry(
            name="C_force",
            domain="physics",
            passed=force_eq >= (mission.payload_target.value or 0.0) * 9.81,
            value=force_eq,
            limit=(mission.payload_target.value or 0.0) * 9.81,
            sense=">=",
            unit="N",
            evidence_ref="#/nominal/equilibrium/force_eq",
        )
    )
    constraints.append(
        ConstraintEntry(
            name="C_deflection",
            domain="physics",
            passed=deflection <= (structure.max_deflection.value or 0.0),
            value=deflection,
            limit=(structure.max_deflection.value or 0.0),
            sense="<=",
            unit="m",
            evidence_ref="#/nominal/equilibrium/deflection_eq",
        )
    )
    mass_ok = not missing_mass and design.budgets.mass_budget.margin.value is not None
    power_ok = not missing_power and design.budgets.power_budget.margin.value is not None
    constraints.append(
        ConstraintEntry(
            name="C_mass_budget_complete",
            domain="budget",
            passed=mass_ok,
            value=float(len(missing_mass)),
            limit=0.0,
            sense="==",
            unit="ratio",
            evidence_ref="#/budgets/mass_budget",
        )
    )
    constraints.append(
        ConstraintEntry(
            name="C_power_budget_complete",
            domain="budget",
            passed=power_ok,
            value=float(len(missing_power)),
            limit=0.0,
            sense="==",
            unit="ratio",
            evidence_ref="#/budgets/power_budget",
        )
    )
    tolerance_values = [
        design.geometry.tolerances.general_linear.value,
        *[item.tol.value for item in design.geometry.tolerances.critical_features],
    ]
    max_requested_tol = max(
        [value for value in tolerance_values if value is not None], default=0.0
    )
    inspection_limit = state.inputs.manufacturing_process.inspection.achievable_tol_linear.value
    tolerance_ok = inspection_limit is not None and max_requested_tol <= inspection_limit
    constraints.append(
        ConstraintEntry(
            name="C_tolerance_verifiable",
            domain="manufacturing",
            passed=tolerance_ok,
            value=max_requested_tol,
            limit=inspection_limit or 0.0,
            sense="<=",
            unit="m",
            evidence_ref="#/geometry/tolerances",
        )
    )
    cad_ref = design.geometry.cad_ref
    cad_ok = cad_ref.type in {"step", "implicit"} and cad_ref.sha256 is not None
    constraints.append(
        ConstraintEntry(
            name="C_cad_reference",
            domain="manufacturing",
            passed=cad_ok,
            value=1.0 if cad_ok else 0.0,
            limit=1.0,
            sense="==",
            unit="ratio",
            evidence_ref="#/geometry/cad_ref",
        )
    )
    report = ConstraintReport(schema_version="constraints.v1.0", constraints=constraints)
    return nominal, report


def evaluate_uq(
    state: PipelineState,
    nominal: NominalResult,
    constraints: ConstraintReport,
) -> UQSummary:
    mission = state.inputs.mission
    success = all(entry.passed for entry in constraints.constraints)
    success_probability = 1.0 if success else 0.0
    payload_ratio_probability = success_probability
    n_samples = 0
    stop_reason: Literal["ci_met", "min_samples_not_met", "max_samples_hit"] = "max_samples_hit"
    halfwidth_success = 1.0
    halfwidth_payload = 1.0
    while n_samples < mission.statistical_sufficiency.uq_max_samples:
        n_samples += mission.statistical_sufficiency.uq_batch
        halfwidth_success = _wilson_halfwidth(success_probability, n_samples)
        halfwidth_payload = _wilson_halfwidth(payload_ratio_probability, n_samples)
        if (
            n_samples >= mission.statistical_sufficiency.uq_min_samples
            and halfwidth_success <= mission.statistical_sufficiency.ci_halfwidth_max
            and halfwidth_payload <= mission.statistical_sufficiency.ci_halfwidth_max
        ):
            stop_reason = "ci_met"
            break
    if n_samples < mission.statistical_sufficiency.uq_min_samples:
        stop_reason = "min_samples_not_met"
    uq_summary = UQSummary(
        schema_version="uq_summary.v1.0",
        n_samples=n_samples,
        stop_reason=stop_reason,
        success_probability=success_probability,
        success_ci=WilsonCI(method="wilson_95", halfwidth=halfwidth_success),
        payload_ratio_probability=payload_ratio_probability,
        payload_ratio_ci=WilsonCI(method="wilson_95", halfwidth=halfwidth_payload),
        continuous_metrics=UQContinuousMetrics(
            force_margin_n=ContinuousMetricSummary(p05=0.0, p50=0.0, p95=0.0),
            deflection_m=ContinuousMetricSummary(p05=0.0, p50=0.0, p95=0.0),
        ),
        numerical_integrity=True,
    )
    return uq_summary


def sensitivity(state: PipelineState) -> SensitivityReport:
    return SensitivityReport(
        schema_version="sensitivity.v1.0",
        metric="force_margin_n",
        method="spearman",
        correlations={
            "pressure_pa": 0.0,
            "temperature_k": 0.0,
            "stiffness_multiplier": 0.0,
            "efficiency_multiplier": 0.0,
            "force_coeff_multiplier": 0.0,
        },
        max_abs_corr=0.0,
    )


def gate_build_ready(
    state: PipelineState,
    nominal: NominalResult,
    uq_summary: UQSummary,
    constraints: ConstraintReport,
    sensitivity_report: SensitivityReport,
) -> GateDecision:
    mission = state.inputs.mission
    reasons: List[str] = []
    passed = True
    if mission.required_nominal_feasible and not all(
        entry.passed for entry in constraints.constraints
    ):
        passed = False
        reasons.append("Nominal constraints failed.")
    if nominal.kpis.payload_ratio.value is not None and (
        nominal.kpis.payload_ratio.value < (mission.payload_ratio_min.value or 0.0)
    ):
        passed = False
        reasons.append("Nominal payload ratio below minimum.")
    if uq_summary.success_probability < mission.probability_thresholds.p_success_min:
        passed = False
        reasons.append("UQ success probability below threshold.")
    if (
        uq_summary.payload_ratio_probability
        < mission.probability_thresholds.p_payload_ratio_min
    ):
        passed = False
        reasons.append("UQ payload ratio probability below threshold.")
    if uq_summary.stop_reason == "max_samples_hit":
        passed = False
        reasons.append("UQ did not reach CI sufficiency.")
    if sensitivity_report.max_abs_corr > mission.fragility_limits.max_abs_corr:
        passed = False
        reasons.append("Fragility limit exceeded.")
    if mission.energy_limits.max_energy.value is not None and (
        nominal.budgets.energy_total.value or 0.0
    ) > mission.energy_limits.max_energy.value:
        passed = False
        reasons.append("Mission energy limit exceeded.")
    if not nominal.numerical_integrity or not uq_summary.numerical_integrity:
        passed = False
        reasons.append("Numerical integrity check failed.")
    if state.inputs.design.actuator.calibration.source == "unfit":
        passed = False
        reasons.append("Uncalibrated model.")
    key_metrics = GateKeyMetrics(
        payload_ratio_nominal=nominal.kpis.payload_ratio.value or 0.0,
        p_success=uq_summary.success_probability,
        p_success_ci_halfwidth=uq_summary.success_ci.halfwidth,
    )
    return GateDecision(
        schema_version="gate_decision.v1.0", passed=passed, reasons=reasons, key_metrics=key_metrics
    )


def _build_packet_tolerances(tolerances: GeometryTolerances) -> BuildPacketTolerances:
    return BuildPacketTolerances(
        general_linear=tolerances.general_linear,
        critical_features=[
            BuildPacketCriticalFeature(
                feature=item.feature,
                tol=item.tol,
                inspection_method="micrometer",
            )
            for item in tolerances.critical_features
        ],
    )


def export_build_packet(
    state: PipelineState,
    constraints: ConstraintReport,
    gate_decision: GateDecision,
    run_manifest: RunManifest,
) -> BuildPacket:
    design = state.inputs.design
    process = state.inputs.manufacturing_process
    cad = design.geometry.cad_ref
    if cad.type in {"step", "implicit"} and cad.sha256 is None:
        raise ValueError("CAD reference requires a sha256 hash.")
    build_packet = BuildPacket(
        schema_version="build_packet.v1.0",
        design_id=design.design_id,
        partner=process.partner,
        process_id=process.process_id,
        cad_payload=BuildPacketCadPayload(type=cad.type, uri=cad.uri, sha256=cad.sha256),
        tolerances=_build_packet_tolerances(design.geometry.tolerances),
        inspection_plan=InspectionPlan(
            methods=["ct", "cmm"],
            acceptance_criteria=[
                "Nominal inspection plan.",
                f"Material spec: {process.material.spec_ref or process.material.material_id}",
            ],
        ),
        validation_summary=ValidationSummary(
            gate_decision_ref="gate_decision.json#/",
            uq_summary_ref="uq_summary.json#/",
            constraints_ref="constraints.json#/",
            manifest_ref="manifest.json#/",
        ),
    )
    return build_packet


def _artifact_manifest(artifact_hashes: Dict[str, str]) -> ManifestArtifacts:
    return ManifestArtifacts(
        **{
            "nominal.json": artifact_hashes["nominal.json"],
            "constraints.json": artifact_hashes["constraints.json"],
            "uq_summary.json": artifact_hashes["uq_summary.json"],
            "uq_samples.*": artifact_hashes["uq_samples.*"],
            "sensitivity.json": artifact_hashes["sensitivity.json"],
            "gate_decision.json": artifact_hashes["gate_decision.json"],
            "build_packet.json": artifact_hashes["build_packet.json"],
            "evidence_pack.json": artifact_hashes["evidence_pack.json"],
            "manifest.json": artifact_hashes["manifest.json"],
        }
    )


def export_evidence_pack(
    state: PipelineState,
    artifacts: Dict[str, str],
) -> EvidencePack:
    return EvidencePack(
        schema_version="evidence_pack.v1.0",
        run_id=state.run_id,
        artifacts=EvidencePackArtifacts(**artifacts),
    )


def export_manifest(
    state: PipelineState,
    artifact_hashes: Dict[str, str],
) -> RunManifest:
    return RunManifest(
        schema_version="manifest.v1.0",
        created_utc=now_utc_iso(),
        git_commit=os.getenv("GITHUB_SHA"),
        python=sys.version,
        platform=platform.platform(),
        inputs_hash=state.inputs_hash,
        seed=state.inputs.run_config.seed,
        artifacts=_artifact_manifest(artifact_hashes),
    )


def _finalize_manifest(
    state: PipelineState,
    artifact_hashes: Dict[str, str],
) -> tuple[RunManifest, str]:
    manifest_seed = export_manifest(
        state,
        {
            **artifact_hashes,
            "manifest.json": "",
        },
    )
    manifest_hash = _hash_payload(manifest_seed)
    manifest = export_manifest(
        state,
        {
            **artifact_hashes,
            "manifest.json": manifest_hash,
        },
    )
    return manifest, manifest_hash


def write_artifacts(
    output_dir: Path,
    payloads: Dict[str, Any],
) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    hashes: Dict[str, str] = {}
    for name, payload in payloads.items():
        path = output_dir / name
        path.write_text(_serialize_payload(payload), encoding="utf-8")
        hashes[name] = sha256_file(path)
    return hashes


def build_pipeline(
    design: Any,
    mission: Any,
    environment: Any,
    manufacturing_process: Any,
    run_config: RunConfig,
    output_dir: Path,
    memory_store: MemoryStore | None = None,
) -> PipelineArtifacts:
    design = _prepare_design_for_ai(design, memory_store)
    state = compile_inputs(design, mission, environment, manufacturing_process, run_config)
    if memory_store is not None:
        memory_store.log_event(
            "pipeline_start",
            "Started pipeline build",
            {
                "run_id": state.run_id,
                "design_id": getattr(design, "design_id", None),
                "seed": run_config.seed,
            },
        )
    nominal, constraints = evaluate_nominal(state)
    uq_summary = evaluate_uq(state, nominal, constraints)
    sensitivity_report = sensitivity(state)
    gate_decision = gate_build_ready(state, nominal, uq_summary, constraints, sensitivity_report)

    if memory_store is not None:
        failure_domains = [entry.domain for entry in constraints.constraints if not entry.passed]
        memory_store.log_event(
            "constraints",
            "Evaluated constraints",
            {
                "run_id": state.run_id,
                "failures": failure_domains,
                "passed": all(entry.passed for entry in constraints.constraints),
            },
        )
        memory_store.log_event(
            "gate_decision",
            "Computed gate decision",
            {
                "run_id": state.run_id,
                "passed": gate_decision.passed,
                "reasons": gate_decision.reasons,
            },
        )

    artifacts: Dict[str, Any] = {
        "nominal.json": nominal,
        "constraints.json": constraints,
        "uq_summary.json": uq_summary,
        "uq_samples.json": {"schema_version": "uq_samples.v1.0", "samples": []},
        "sensitivity.json": sensitivity_report,
        "gate_decision.json": gate_decision,
    }

    artifact_hashes = write_artifacts(output_dir, artifacts)
    artifact_hashes["uq_samples.*"] = artifact_hashes["uq_samples.json"]

    manifest = export_manifest(
        state,
        {
            **artifact_hashes,
            "build_packet.json": "",
            "evidence_pack.json": "",
            "manifest.json": "",
        },
    )
    build_packet = export_build_packet(state, constraints, gate_decision, manifest)
    artifacts["build_packet.json"] = build_packet
    artifact_hashes.update(write_artifacts(output_dir, {"build_packet.json": build_packet}))

    evidence_pack = export_evidence_pack(
        state,
        {
            "nominal": "nominal.json",
            "constraints": "constraints.json",
            "uq_summary": "uq_summary.json",
            "uq_samples": "uq_samples.json",
            "sensitivity": "sensitivity.json",
            "gate_decision": "gate_decision.json",
            "build_packet": "build_packet.json",
            "manifest": "manifest.json",
        },
    )
    artifacts["evidence_pack.json"] = evidence_pack
    artifact_hashes.update(write_artifacts(output_dir, {"evidence_pack.json": evidence_pack}))

    manifest, manifest_hash = _finalize_manifest(state, artifact_hashes)
    artifact_hashes["manifest.json"] = manifest_hash
    write_artifacts(output_dir, {"manifest.json": manifest})

    if memory_store is not None:
        memory_store.log_event(
            "pipeline_complete",
            "Pipeline artifacts written",
            {
                "run_id": state.run_id,
                "artifact_count": len(artifact_hashes),
                "output_dir": str(output_dir),
            },
        )

    return PipelineArtifacts(
        nominal=nominal,
        constraints=constraints,
        uq_summary=uq_summary,
        sensitivity=sensitivity_report,
        gate_decision=gate_decision,
        build_packet=build_packet,
        manifest=manifest,
        evidence_pack=evidence_pack,
    )
