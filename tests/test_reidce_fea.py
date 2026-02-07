from reidce.fea import (
    BoundaryCondition,
    PointLoad,
    evaluate_design_fea,
    generate_beam_mesh,
    solve_static,
)
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
        design_id="fea_test_001",
        name="fea_baseline",
        domain="actuated_compliant_subsystem",
        geometry=GeometrySpec(
            schema_version="geometry.v1.0",
            cad_ref=CadRef(type="none", uri=None, sha256=None),
            envelope_max=_quantity(0.2, "m"),
            key_dimensions=GeometryKeyDimensions(
                actuator_diameter=_quantity(0.02, "m"),
                actuator_wall_thickness=_quantity(0.002, "m"),
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
            diameter=_quantity(0.02, "m"),
            wall_thickness=_quantity(0.002, "m"),
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


def test_generate_beam_mesh() -> None:
    design = _make_design()
    mesh = generate_beam_mesh(design, n_elements=10)
    assert mesh.node_count == 11
    assert mesh.element_count == 10
    assert len(mesh.nodes) == 11
    assert len(mesh.elements) == 10


def test_beam_mesh_node_positions() -> None:
    design = _make_design()
    mesh = generate_beam_mesh(design, n_elements=5)
    assert mesh.nodes[0].z == 0.0
    assert abs(mesh.nodes[-1].z - 0.2) < 1e-9


def test_solve_static_cantilever() -> None:
    design = _make_design()
    mesh = generate_beam_mesh(design, n_elements=10)
    bcs = [
        BoundaryCondition(node_id=0, dof="uz", value=0.0),
        BoundaryCondition(node_id=0, dof="ux", value=0.0),
    ]
    loads = [PointLoad(node_id=10, fx=5.0)]
    result = solve_static(mesh, bcs, loads)
    assert result.converged is True
    assert result.max_displacement_m > 0.0
    assert result.max_von_mises_pa > 0.0


def test_solve_static_no_load() -> None:
    design = _make_design()
    mesh = generate_beam_mesh(design, n_elements=5)
    bcs = [
        BoundaryCondition(node_id=0, dof="uz", value=0.0),
        BoundaryCondition(node_id=0, dof="ux", value=0.0),
    ]
    result = solve_static(mesh, bcs, loads=[])
    assert result.converged is True
    assert result.max_displacement_m < 1e-10


def test_evaluate_design_fea() -> None:
    design = _make_design()
    result = evaluate_design_fea(design, tip_load_n=10.0, n_elements=8)
    assert result.converged is True
    assert len(result.nodal_displacements) == 9
    assert len(result.element_stresses) == 8
    assert result.max_displacement_m > 0.0


def test_safety_factor_positive() -> None:
    design = _make_design()
    result = evaluate_design_fea(design, tip_load_n=5.0)
    for stress in result.element_stresses:
        assert stress.safety_factor > 0.0


def test_tip_displacement_increases_with_load() -> None:
    design = _make_design()
    result_low = evaluate_design_fea(design, tip_load_n=5.0)
    result_high = evaluate_design_fea(design, tip_load_n=50.0)
    assert result_high.max_displacement_m > result_low.max_displacement_m


def test_von_mises_uses_abs_sum_for_opposite_sign_stresses() -> None:
    """Von Mises (max fiber) stress must equal |axial| + |bending|.

    When axial and bending stresses have opposite signs, the old formula
    ``abs(axial + bending)`` would undercount the peak fiber stress.
    """
    design = _make_design()
    mesh = generate_beam_mesh(design, n_elements=10)
    bcs = [
        BoundaryCondition(node_id=0, dof="uz", value=0.0),
        BoundaryCondition(node_id=0, dof="ux", value=0.0),
    ]
    # Apply both axial (fz) and transverse (fx) loads so that at least some
    # elements develop axial and bending stresses with opposite signs.
    loads = [PointLoad(node_id=10, fx=5.0, fz=-10.0)]
    result = solve_static(mesh, bcs, loads)
    assert result.converged is True

    for es in result.element_stresses:
        expected = abs(es.axial_stress_pa) + abs(es.bending_stress_pa)
        assert abs(es.von_mises_pa - expected) < 1e-6, (
            f"element {es.element_id}: von_mises_pa={es.von_mises_pa} "
            f"!= |axial|+|bending|={expected}"
        )
