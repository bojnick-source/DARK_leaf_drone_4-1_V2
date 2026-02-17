from __future__ import annotations

from reidce import prepare_design_for_pipeline
from reidce.memory import MemoryStore
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


def test_prepare_design_for_pipeline_adds_cad_ref() -> None:
    """Test that prepare_design_for_pipeline applies PicoGK CAD ref."""
    design = _make_design()
    updated = prepare_design_for_pipeline(design)
    assert updated.geometry.cad_ref.type == "implicit"
    assert updated.geometry.cad_ref.sha256
    assert updated.geometry.cad_ref.uri is not None
    assert updated.geometry.cad_ref.uri.startswith("pico_gk://")


def test_prepare_design_for_pipeline_with_memory_store() -> None:
    """Test that prepare_design_for_pipeline logs events to memory store."""
    design = _make_design()
    memory_store = MemoryStore()
    updated = prepare_design_for_pipeline(design, memory_store)
    
    # Check that PicoGK event was logged
    events = [record for record in memory_store.records if "pico_gk" in record.tags]
    assert len(events) == 1
    assert events[0].text == "Applied Pico GK CAD ref"
    
    # Check that topology event was logged
    events = [
        record for record in memory_store.records if "topology_recommendation" in record.tags
    ]
    assert len(events) == 1
    assert events[0].text == "Selected topology candidate"
    
    # Check that design was updated
    assert updated.geometry.cad_ref.type == "implicit"
    assert (
        updated.name.endswith("_topology_1")
        or updated.name.endswith("_topology_2")
        or updated.name.endswith("_topology_3")
    )


def test_prepare_design_for_pipeline_skips_non_design_objects() -> None:
    """Test that prepare_design_for_pipeline handles non-design objects gracefully."""
    non_design = {"foo": "bar"}
    result = prepare_design_for_pipeline(non_design)
    assert result == non_design
