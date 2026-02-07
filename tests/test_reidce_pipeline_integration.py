from __future__ import annotations

from pathlib import Path
from typing import Literal

from reidce.memory import MemoryStore
from reidce.pipeline import build_pipeline
from reidce.schemas import (
    ActuatorSpec,
    BudgetLine,
    BudgetsSpec,
    CadRef,
    CalibrationParamsUncertainty,
    CalibrationSpec,
    DesignSpec,
    DistributionParams,
    DistributionSpec,
    EnvironmentSpec,
    FragilityLimits,
    GeometryKeyDimensions,
    GeometrySpec,
    GeometryTolerances,
    InspectionSpec,
    ManufacturingProcessSpec,
    MassBudget,
    MaterialSpec,
    MissionEnergyLimits,
    MissionSpec,
    PowerBudget,
    ProbabilityThresholds,
    ProcessCapability,
    Quantity,
    RunConfig,
    StatisticalSufficiency,
    StructureSpec,
    UnitLiteral,
    VariabilitySpec,
)

DistributionUnit = Literal["kg", "N", "W", "Pa", "K", "m", "ratio", "deg"]


def _quantity(value: float, unit: UnitLiteral) -> Quantity:
    return Quantity(value=value, unit=unit)


def _delta(value: float, unit: DistributionUnit) -> DistributionSpec:
    return DistributionSpec(
        dist="delta",
        params=DistributionParams(mean=value),
        unit=unit,
        notes="",
    )


def _make_design() -> DesignSpec:
    return DesignSpec(
        schema_version="design.v1.0",
        design_id="design_200",
        name="baseline",
        domain="actuated_compliant_subsystem",
        geometry=GeometrySpec(
            schema_version="geometry.v1.0",
            cad_ref=CadRef(type="none", uri=None, sha256=None),
            envelope_max=_quantity(0.2, "m"),
            key_dimensions=GeometryKeyDimensions(
                actuator_diameter=_quantity(0.01, "m"),
                actuator_wall_thickness=_quantity(0.001, "m"),
                actuator_length=_quantity(0.2, "m"),
            ),
            tolerances=GeometryTolerances(
                general_linear=_quantity(0.0001, "m"),
                critical_linear=_quantity(0.00005, "m"),
                critical_features=[],
            ),
        ),
        actuator=ActuatorSpec(
            schema_version="actuator.mckibben.v1.0",
            diameter=_quantity(0.01, "m"),
            wall_thickness=_quantity(0.001, "m"),
            length=_quantity(0.2, "m"),
            max_strain=_quantity(0.2, "ratio"),
            pressure_limit=_quantity(200000.0, "Pa"),
            force_coeff=_quantity(0.8, "ratio"),
            efficiency=_quantity(0.75, "ratio"),
            calibration=CalibrationSpec(
                schema_version="calibration.v1.0",
                source="bench_test",
                fit_date_utc=None,
                params_uncertainty=CalibrationParamsUncertainty(
                    force_coeff_dist=None,
                    efficiency_dist=None,
                ),
            ),
        ),
        structure=StructureSpec(
            schema_version="structure.compliance.v1.0",
            stiffness=_quantity(1000.0, "N/m"),
            stiffness_unit_note="N/m explicit",
            stiffness_n_per_m=_quantity(1000.0, "ratio"),
            max_deflection=_quantity(0.01, "m"),
        ),
        budgets=BudgetsSpec(
            schema_version="budgets.v1.0",
            mass_budget=MassBudget(
                currency="kg",
                margin=_quantity(0.1, "kg"),
                lines=[
                    BudgetLine(
                        name="frame",
                        mass=_quantity(0.5, "kg"),
                        power=None,
                        owner="structures",
                        required=True,
                    )
                ],
            ),
            power_budget=PowerBudget(
                currency="W",
                margin=_quantity(10.0, "W"),
                lines=[
                    BudgetLine(
                        name="pump",
                        mass=None,
                        power=_quantity(50.0, "W"),
                        owner="propulsion",
                        required=True,
                    )
                ],
            ),
        ),
    )


def _make_mission() -> MissionSpec:
    return MissionSpec(
        schema_version="mission.v1.0",
        mission_id="mission_200",
        payload_target=_quantity(2.0, "kg"),
        duration=_quantity(60.0, "s"),
        payload_ratio_min=_quantity(0.1, "ratio"),
        probability_thresholds=ProbabilityThresholds(p_success_min=0.0, p_payload_ratio_min=0.0),
        statistical_sufficiency=StatisticalSufficiency(
            ci_method="wilson_95",
            ci_halfwidth_max=1.0,
            uq_min_samples=1,
            uq_max_samples=1,
            uq_batch=1,
        ),
        fragility_limits=FragilityLimits(sensitivity_metric="spearman", max_abs_corr=1.0),
        required_nominal_feasible=False,
        energy_limits=MissionEnergyLimits(max_energy=_quantity(1.0e9, "J")),
    )


def _make_environment() -> EnvironmentSpec:
    return EnvironmentSpec(
        schema_version="env.v1.0",
        pressure=_delta(101325.0, "Pa"),
        temperature=_delta(293.15, "K"),
    )


def _make_manufacturing() -> ManufacturingProcessSpec:
    return ManufacturingProcessSpec(
        schema_version="mfg_process.v1.0",
        process_id="mfg_200",
        partner="TestLab",
        process_name="Sample Process",
        material=MaterialSpec(material_id="mat_200", spec_ref=None),
        capability=ProcessCapability(
            max_build_envelope=_quantity(1.0, "m"),
            min_feature=_quantity(0.001, "m"),
            min_wall=_quantity(0.001, "m"),
            min_radius=_quantity(0.001, "m"),
            tolerance_linear=_quantity(0.0001, "m"),
            max_overhang=_quantity(30.0, "deg"),
        ),
        inspection=InspectionSpec(
            schema_version="inspection.v1.0",
            methods=["ct"],
            achievable_tol_linear=_quantity(0.0002, "m"),
            notes="Nominal inspection",
        ),
        variability=VariabilitySpec(
            stiffness_multiplier=_delta(1.0, "ratio"),
            efficiency_multiplier=_delta(1.0, "ratio"),
            force_coeff_multiplier=_delta(1.0, "ratio"),
        ),
        process_window_version="1.0",
        valid_from_utc="2026-02-04T00:00:00Z",
        valid_to_utc=None,
    )


def _make_run_config(tmp_path: Path) -> RunConfig:
    return RunConfig(
        schema_version="run_config.v1.0",
        seed=42,
        save_dir=str(tmp_path / "artifacts"),
        label="test",
        enable_trace=False,
        store_samples=False,
        sample_store_format="json",
    )


def test_pipeline_applies_pico_gk_and_topology(tmp_path: Path) -> None:
    memory_store = MemoryStore()
    artifacts = build_pipeline(
        design=_make_design(),
        mission=_make_mission(),
        environment=_make_environment(),
        manufacturing_process=_make_manufacturing(),
        run_config=_make_run_config(tmp_path),
        output_dir=tmp_path / "artifacts",
        memory_store=memory_store,
    )

    assert artifacts.build_packet.cad_payload.type == "implicit"
    assert artifacts.build_packet.cad_payload.sha256

    tags = [tag for record in memory_store.records for tag in record.tags]
    assert "pico_gk" in tags
    assert "topology_recommendation" in tags


def test_pipeline_uses_standard_gravity(tmp_path: Path) -> None:
    """Payload ratio must use standard gravity 9.80665, not 9.81."""
    from reidce.pipeline import _GRAVITY_M_S2, compile_inputs, evaluate_nominal

    design = _make_design()
    mission = _make_mission()
    state = compile_inputs(
        design=design,
        mission=mission,
        environment=_make_environment(),
        manufacturing_process=_make_manufacturing(),
        run_config=_make_run_config(tmp_path),
    )
    nominal, constraints = evaluate_nominal(state)
    force_eq = nominal.equilibrium.force_eq.value
    assert force_eq is not None
    expected_ratio = (force_eq / _GRAVITY_M_S2) / mission.payload_target.value
    assert abs(nominal.kpis.payload_ratio.value - expected_ratio) < 1e-12
    # Verify the constant is the standard value
    assert _GRAVITY_M_S2 == 9.80665
