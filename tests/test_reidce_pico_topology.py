from reidce.design_prep import apply_pico_gk
from reidce.schemas import (
    ActuatorSpec,
    BudgetLine,
    BudgetsSpec,
    CadRef,
    CalibrationParamsUncertainty,
    CalibrationSpec,
    DesignSpec,
    GeometryKeyDimensions,
    GeometrySpec,
    GeometryTolerances,
    MassBudget,
    PowerBudget,
    Quantity,
    StructureSpec,
    UnitLiteral,
)
from reidce.topology import generate_topology_candidates, recommend_topology


def _quantity(value: float, unit: UnitLiteral) -> Quantity:
    return Quantity(value=value, unit=unit)


def _make_design() -> DesignSpec:
    return DesignSpec(
        schema_version="design.v1.0",
        design_id="design_001",
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
                        power=_quantity(50.0, "W"),
                        owner="propulsion",
                        required=True,
                    )
                ],
            ),
        ),
    )


def test_apply_pico_gk_adds_cad_ref() -> None:
    design = _make_design()
    updated = apply_pico_gk(design)
    assert updated.geometry.cad_ref.type == "implicit"
    assert updated.geometry.cad_ref.sha256
    assert updated.geometry.cad_ref.uri is not None
    assert updated.geometry.cad_ref.uri.startswith("pico_gk://")


def test_apply_pico_gk_skips_existing_cad_ref() -> None:
    base_design = _make_design()
    design = base_design.model_copy(
        update={
            "geometry": base_design.geometry.model_copy(
                update={"cad_ref": CadRef(type="step", uri="file.step", sha256="abc")}
            )
        }
    )
    updated = apply_pico_gk(design)
    assert updated.geometry.cad_ref.type == "step"
    assert updated.geometry.cad_ref.uri == "file.step"


def test_generate_topology_candidates() -> None:
    design = _make_design()
    candidates = generate_topology_candidates(design)
    assert len(candidates) == 3
    candidate_names = {candidate.design.name for candidate in candidates}
    assert any(name.endswith("_topology_1") for name in candidate_names)
    assert any(name.endswith("_topology_2") for name in candidate_names)
    assert any(name.endswith("_topology_3") for name in candidate_names)


def test_recommend_topology() -> None:
    design = _make_design()
    recommendation = recommend_topology(design)
    assert recommendation.best.name.startswith("baseline_topology_")
    assert len(recommendation.ranked) == 3


def test_deflection_capacity_uses_energy_formula() -> None:
    """deflection_capacity must use 0.5 * k * δ² (elastic energy), not k * δ."""
    design = _make_design()
    candidates = generate_topology_candidates(design)
    for candidate in candidates:
        k = candidate.metrics["stiffness_n_per_m"]
        d = candidate.metrics["max_deflection_m"]
        expected = 0.5 * k * d * d
        assert abs(candidate.metrics["deflection_capacity"] - expected) < 1e-12
