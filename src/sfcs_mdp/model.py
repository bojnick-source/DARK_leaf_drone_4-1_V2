from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class StepType(str, Enum):
    GATE = "GATE"
    PROCESS = "PROCESS"


class AcceptanceCriterionType(str, Enum):
    FILE_EXISTS = "file_exists"
    MANUAL_SIGNOFF = "manual_signoff"


class StepDisposition(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    OPTIONAL = "OPTIONAL"


class BlockLevel(str, Enum):
    BLOCK_0_STRUCTURE_ONLY = "BLOCK_0_STRUCTURE_ONLY"
    BLOCK_1_STRUCTURAL_SENSING = "BLOCK_1_STRUCTURAL_SENSING"
    BLOCK_2_POWER_DISTRIBUTION = "BLOCK_2_POWER_DISTRIBUTION"
    BLOCK_3_DISTRIBUTED_ELECTRONICS = "BLOCK_3_DISTRIBUTED_ELECTRONICS"
    BLOCK_4_ENERGY_STORAGE_INTEGRATION = "BLOCK_4_ENERGY_STORAGE_INTEGRATION"


class MaturityLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: BlockLevel
    goal: str


class MaturityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    levels: List[MaturityLevel]


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program: str
    owner: str
    scope: str
    exclusions: List[str]
    maturity_model: MaturityModel


class Toolpaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    afp_paths: str
    insert_placement: str
    machining_ops: str


class ProcessParameterSets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    afp: str
    cure_cycle: str
    bonding_surface_prep: str
    optical_embed_rules: str
    electrical_embed_rules: str
    ndi_plan: str
    metrology_plan: str


class SingleSourceOfTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_registry: str
    requirements_db: str
    cad_revision: str
    toolpaths: Toolpaths
    process_parameter_sets: ProcessParameterSets


class BuildManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields_required: List[str]
    output: str


class DigitalThread(BaseModel):
    model_config = ConfigDict(extra="forbid")

    single_source_of_truth: SingleSourceOfTruth
    build_manifest: BuildManifest


class ConfigurationManagement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: List[str]


class MrbDisposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    options: List[str]


class Nonconformance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ncr_record: str
    mrb_disposition: MrbDisposition


class FirstArticleInspection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_for: List[str]
    evidence_package: str


class AcceptanceDataPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_artifacts: List[str]


class QualitySystem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configuration_management: ConfigurationManagement
    nonconformance: Nonconformance
    first_article_inspection: FirstArticleInspection
    acceptance_data_package: AcceptanceDataPackage


AcceptanceCriterion = Union[str, Dict[str, object]]


class Acceptance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criteria: List[AcceptanceCriterion]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: List[str] = Field(default_factory=list)


class WhenCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_level_at_least: BlockLevel


class ProcessStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    name: str
    type: StepType
    prerequisites: List[str] = Field(default_factory=list)
    when: Optional[WhenCondition] = None
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    acceptance: Acceptance
    evidence: Evidence


class InstrumentationMinimum(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manufacturing: List[str]
    embedded_systems: List[str]


class RiskItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    risk: str
    mitigation: List[str]


class Spec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: Meta
    digital_thread: DigitalThread
    quality_system: QualitySystem
    process_flow: List[ProcessStep]
    instrumentation_minimum: InstrumentationMinimum
    risk_register_top: List[RiskItem]
