from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

UnitLiteral = Literal[
    "kg",
    "N",
    "W",
    "Pa",
    "K",
    "m",
    "s",
    "J",
    "ratio",
    "deg",
    "N/m",
    "N_per_m",
]


class Quantity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Optional[float]
    unit: UnitLiteral


class DistributionParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    mode: Optional[float] = None


class DistributionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dist: Literal["normal", "lognormal", "uniform", "triangular", "delta"]
    params: DistributionParams
    unit: Literal["kg", "N", "W", "Pa", "K", "m", "ratio", "deg"]
    notes: str


class CadRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["none", "step", "parasolid", "implicit"]
    uri: Optional[str]
    sha256: Optional[str]


class CriticalFeatureTolerance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature: str
    tol: Quantity


class GeometryTolerances(BaseModel):
    model_config = ConfigDict(extra="forbid")

    general_linear: Quantity
    critical_linear: Quantity
    critical_features: List[CriticalFeatureTolerance]


class GeometryKeyDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actuator_diameter: Quantity
    actuator_wall_thickness: Quantity
    actuator_length: Quantity


class GeometrySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["geometry.v1.0"]
    cad_ref: CadRef
    envelope_max: Quantity
    key_dimensions: GeometryKeyDimensions
    tolerances: GeometryTolerances


class CalibrationParamsUncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force_coeff_dist: Optional[DistributionSpec]
    efficiency_dist: Optional[DistributionSpec]


class CalibrationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["calibration.v1.0"]
    source: Literal["unfit", "bench_test", "vendor_curve"]
    fit_date_utc: Optional[str]
    params_uncertainty: CalibrationParamsUncertainty


class ActuatorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["actuator.mckibben.v1.0"]
    diameter: Quantity
    wall_thickness: Quantity
    length: Quantity
    max_strain: Quantity
    pressure_limit: Quantity
    force_coeff: Quantity
    efficiency: Quantity
    calibration: CalibrationSpec


class StructureSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["structure.compliance.v1.0"]
    stiffness: Quantity
    stiffness_unit_note: str
    stiffness_n_per_m: Quantity
    max_deflection: Quantity


class BudgetLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    mass: Optional[Quantity] = None
    power: Optional[Quantity] = None
    owner: str
    required: bool


class MassBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: Literal["kg"]
    margin: Quantity
    lines: List[BudgetLine]


class PowerBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: Literal["W"]
    margin: Quantity
    lines: List[BudgetLine]


class BudgetsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["budgets.v1.0"]
    mass_budget: MassBudget
    power_budget: PowerBudget


class DesignSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["design.v1.0"]
    design_id: str
    name: str
    domain: Literal["actuated_compliant_subsystem"]
    geometry: GeometrySpec
    actuator: ActuatorSpec
    structure: StructureSpec
    budgets: BudgetsSpec


class ProbabilityThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p_success_min: float
    p_payload_ratio_min: float


class StatisticalSufficiency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ci_method: Literal["wilson_95"]
    ci_halfwidth_max: float
    uq_min_samples: int
    uq_max_samples: int
    uq_batch: int


class FragilityLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensitivity_metric: Literal["spearman"]
    max_abs_corr: float


class MissionEnergyLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_energy: Quantity


class MissionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["mission.v1.0"]
    mission_id: str
    payload_target: Quantity
    duration: Quantity
    payload_ratio_min: Quantity
    probability_thresholds: ProbabilityThresholds
    statistical_sufficiency: StatisticalSufficiency
    fragility_limits: FragilityLimits
    required_nominal_feasible: bool
    energy_limits: MissionEnergyLimits


class EnvironmentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["env.v1.0"]
    pressure: DistributionSpec
    temperature: DistributionSpec


class MaterialSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_id: str
    spec_ref: Optional[str]


class ProcessCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_build_envelope: Quantity
    min_feature: Quantity
    min_wall: Quantity
    min_radius: Quantity
    tolerance_linear: Quantity
    max_overhang: Quantity


class InspectionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["inspection.v1.0"]
    methods: List[Literal["ct", "cmm", "laser_scan", "micrometer", "none"]]
    achievable_tol_linear: Quantity
    notes: str


class VariabilitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stiffness_multiplier: DistributionSpec
    efficiency_multiplier: DistributionSpec
    force_coeff_multiplier: DistributionSpec


class ManufacturingProcessSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["mfg_process.v1.0"]
    process_id: str
    partner: str
    process_name: str
    material: MaterialSpec
    capability: ProcessCapability
    inspection: InspectionSpec
    variability: VariabilitySpec
    process_window_version: str
    valid_from_utc: str
    valid_to_utc: Optional[str]


class RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["run_config.v1.0"]
    seed: int
    save_dir: str
    label: str
    enable_trace: bool
    store_samples: bool
    sample_store_format: Literal["json", "npz", "parquet"]


class ConstraintEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    domain: Literal["physics", "budget", "manufacturing"]
    passed: bool
    value: float
    limit: float
    sense: Literal[">=", "<=", "=="]
    unit: Literal["N", "m", "kg", "W", "J", "ratio"]
    evidence_ref: str


class ConstraintReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["constraints.v1.0"]
    constraints: List[ConstraintEntry]


class EquilibriumSolverSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    rtol: float
    atol: float
    maxiter: int


class NominalEquilibrium(BaseModel):
    model_config = ConfigDict(extra="forbid")

    converged: bool
    strain_star: Quantity
    force_eq: Quantity
    deflection_eq: Quantity
    residual_force: Quantity
    solver: EquilibriumSolverSpec


class BudgetTotals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mass_total: Quantity
    power_total: Quantity
    energy_total: Quantity


class KPIResults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload_ratio: Quantity
    useful_work_n_per_w: Quantity


class NominalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["nominal.v1.0"]
    equilibrium: NominalEquilibrium
    budgets: BudgetTotals
    kpis: KPIResults
    numerical_integrity: bool


class WilsonCI(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["wilson_95"]
    halfwidth: float


class ContinuousMetricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p05: float
    p50: float
    p95: float


class UQContinuousMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force_margin_n: ContinuousMetricSummary
    deflection_m: ContinuousMetricSummary


class UQSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["uq_summary.v1.0"]
    n_samples: int
    stop_reason: Literal["ci_met", "min_samples_not_met", "max_samples_hit"]
    success_probability: float
    success_ci: WilsonCI
    payload_ratio_probability: float
    payload_ratio_ci: WilsonCI
    continuous_metrics: UQContinuousMetrics
    numerical_integrity: bool


class SensitivityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["sensitivity.v1.0"]
    metric: Literal["force_margin_n", "success", "deflection_m"]
    method: Literal["spearman"]
    correlations: Dict[
        Literal[
            "pressure_pa",
            "temperature_k",
            "stiffness_multiplier",
            "efficiency_multiplier",
            "force_coeff_multiplier",
        ],
        float,
    ]
    max_abs_corr: float


class GateKeyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload_ratio_nominal: float
    p_success: float
    p_success_ci_halfwidth: float


class GateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["gate_decision.v1.0"]
    passed: bool
    reasons: List[str]
    key_metrics: GateKeyMetrics


class BuildPacketCadPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["step", "parasolid", "implicit", "none"]
    uri: Optional[str]
    sha256: Optional[str]


class BuildPacketCriticalFeature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature: str
    tol: Quantity
    inspection_method: Literal["ct", "cmm", "laser_scan", "micrometer"]


class BuildPacketTolerances(BaseModel):
    model_config = ConfigDict(extra="forbid")

    general_linear: Quantity
    critical_features: List[BuildPacketCriticalFeature]


class InspectionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    methods: List[Literal["ct", "cmm"]]
    acceptance_criteria: List[str]


class ValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_decision_ref: str
    uq_summary_ref: str
    constraints_ref: str
    manifest_ref: str


class BuildPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["build_packet.v1.0"]
    design_id: str
    partner: str
    process_id: str
    cad_payload: BuildPacketCadPayload
    tolerances: BuildPacketTolerances
    inspection_plan: InspectionPlan
    validation_summary: ValidationSummary


class ManifestInputsHash(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design: str
    mission: str
    environment: str
    manufacturing_process: str
    run_config: str


class ManifestArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nominal_json: str = Field(alias="nominal.json")
    constraints_json: str = Field(alias="constraints.json")
    uq_summary_json: str = Field(alias="uq_summary.json")
    uq_samples: str = Field(alias="uq_samples.*")
    sensitivity_json: str = Field(alias="sensitivity.json")
    gate_decision_json: str = Field(alias="gate_decision.json")
    build_packet_json: str = Field(alias="build_packet.json")
    evidence_pack_json: str = Field(alias="evidence_pack.json")
    manifest_json: str = Field(alias="manifest.json")


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal["manifest.v1.0"]
    created_utc: str
    git_commit: Optional[str]
    python: str
    platform: str
    inputs_hash: ManifestInputsHash
    seed: int
    artifacts: ManifestArtifacts


class EvidencePackArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nominal: str
    constraints: str
    uq_summary: str
    uq_samples: str
    sensitivity: str
    gate_decision: str
    build_packet: str
    manifest: str


class EvidencePack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["evidence_pack.v1.0"]
    run_id: str
    artifacts: EvidencePackArtifacts


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
