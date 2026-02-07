from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Literal, Sequence

from reidce.schemas import DesignSpec


@dataclass(frozen=True)
class Node:
    node_id: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class BeamElement:
    element_id: int
    node_i: int
    node_j: int
    area_m2: float
    moment_of_inertia_m4: float
    elastic_modulus_pa: float
    length_m: float


@dataclass(frozen=True)
class BoundaryCondition:
    node_id: int
    dof: Literal["ux", "uy", "uz", "rx", "ry", "rz"]
    value: float = 0.0


@dataclass(frozen=True)
class PointLoad:
    node_id: int
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0


@dataclass(frozen=True)
class NodalResult:
    node_id: int
    ux: float
    uy: float
    uz: float
    rx: float
    ry: float
    rz: float


@dataclass(frozen=True)
class ElementStress:
    element_id: int
    axial_stress_pa: float
    bending_stress_pa: float
    von_mises_pa: float
    safety_factor: float


@dataclass(frozen=True)
class FEAResult:
    converged: bool
    nodal_displacements: List[NodalResult]
    element_stresses: List[ElementStress]
    max_displacement_m: float
    max_von_mises_pa: float
    total_strain_energy_j: float


@dataclass(frozen=True)
class FEAMesh:
    nodes: List[Node]
    elements: List[BeamElement]
    node_count: int
    element_count: int


def _beam_stiffness_local(element: BeamElement) -> List[List[float]]:
    """Compute the local stiffness matrix for a 2-node Euler-Bernoulli beam.

    Returns a 4x4 reduced stiffness matrix for axial + bending in one plane:
      DOFs: [u_i, w_i, u_j, w_j] (axial, transverse at each node).
    """
    e = element.elastic_modulus_pa
    a = element.area_m2
    i_val = element.moment_of_inertia_m4
    ll = element.length_m

    if ll < 1e-12:
        return [[0.0] * 4 for _ in range(4)]

    ea_l = e * a / ll
    ei_l3 = 12.0 * e * i_val / (ll**3)

    return [
        [ea_l, 0.0, -ea_l, 0.0],
        [0.0, ei_l3, 0.0, -ei_l3],
        [-ea_l, 0.0, ea_l, 0.0],
        [0.0, -ei_l3, 0.0, ei_l3],
    ]


def generate_beam_mesh(
    design: DesignSpec,
    n_elements: int = 10,
    elastic_modulus_pa: float = 2.0e9,
) -> FEAMesh:
    """Generate a 1D beam FEA mesh from a design spec.

    The actuator is modeled as a cantilever beam along the Z axis.
    """
    dims = design.geometry.key_dimensions
    diameter = dims.actuator_diameter.value or 0.01
    wall_thickness = dims.actuator_wall_thickness.value or 0.001
    length = dims.actuator_length.value or 0.2

    r_outer = diameter / 2.0
    r_inner = max(r_outer - wall_thickness, 0.0)

    area = math.pi * (r_outer**2 - r_inner**2)
    moment_of_inertia = math.pi / 4.0 * (r_outer**4 - r_inner**4)

    element_length = length / n_elements

    nodes: List[Node] = []
    for i in range(n_elements + 1):
        z = i * element_length
        nodes.append(Node(node_id=i, x=0.0, y=0.0, z=z))

    elements: List[BeamElement] = []
    for i in range(n_elements):
        elements.append(
            BeamElement(
                element_id=i,
                node_i=i,
                node_j=i + 1,
                area_m2=area,
                moment_of_inertia_m4=moment_of_inertia,
                elastic_modulus_pa=elastic_modulus_pa,
                length_m=element_length,
            )
        )

    return FEAMesh(
        nodes=nodes,
        elements=elements,
        node_count=len(nodes),
        element_count=len(elements),
    )


def solve_static(
    mesh: FEAMesh,
    boundary_conditions: Sequence[BoundaryCondition],
    loads: Sequence[PointLoad],
    yield_stress_pa: float = 250e6,
) -> FEAResult:
    """Solve a static FEA problem using direct stiffness method.

    Uses a simplified 2-DOF-per-node approach (axial u_z + transverse u_x)
    for the beam model, solving K·d = F by Gaussian elimination.
    """
    n_nodes = mesh.node_count
    n_dof = 2 * n_nodes  # 2 DOFs per node: axial (uz) and transverse (ux)

    # Assemble global stiffness matrix
    k_global = [[0.0] * n_dof for _ in range(n_dof)]
    f_global = [0.0] * n_dof

    for elem in mesh.elements:
        k_local = _beam_stiffness_local(elem)
        # Map local DOFs to global: [u_i_axial, u_i_transverse, u_j_axial, u_j_transverse]
        dof_map = [
            2 * elem.node_i,
            2 * elem.node_i + 1,
            2 * elem.node_j,
            2 * elem.node_j + 1,
        ]
        for i_local in range(4):
            for j_local in range(4):
                i_global = dof_map[i_local]
                j_global = dof_map[j_local]
                k_global[i_global][j_global] += k_local[i_local][j_local]

    # Apply loads
    for load in loads:
        idx_axial = 2 * load.node_id
        idx_transverse = 2 * load.node_id + 1
        if idx_axial < n_dof:
            f_global[idx_axial] += load.fz  # axial along Z
        if idx_transverse < n_dof:
            f_global[idx_transverse] += load.fx  # transverse along X

    # Apply boundary conditions (penalty method)
    penalty = 1e20
    for bc in boundary_conditions:
        if bc.dof == "uz":
            idx = 2 * bc.node_id
        elif bc.dof == "ux":
            idx = 2 * bc.node_id + 1
        else:
            continue
        if idx < n_dof:
            k_global[idx][idx] += penalty
            f_global[idx] += penalty * bc.value

    # Solve K·d = F using Gaussian elimination with partial pivoting
    d = _solve_linear_system(k_global, f_global)

    # Extract nodal displacements
    nodal_displacements: List[NodalResult] = []
    max_disp = 0.0
    for i in range(n_nodes):
        uz = d[2 * i] if 2 * i < len(d) else 0.0
        ux = d[2 * i + 1] if 2 * i + 1 < len(d) else 0.0
        disp_mag = math.sqrt(uz**2 + ux**2)
        max_disp = max(max_disp, disp_mag)
        nodal_displacements.append(
            NodalResult(
                node_id=i,
                ux=ux,
                uy=0.0,
                uz=uz,
                rx=0.0,
                ry=0.0,
                rz=0.0,
            )
        )

    # Compute element stresses
    element_stresses: List[ElementStress] = []
    max_vm = 0.0
    total_strain_energy = 0.0

    for elem in mesh.elements:
        uz_i = d[2 * elem.node_i] if 2 * elem.node_i < len(d) else 0.0
        uz_j = d[2 * elem.node_j] if 2 * elem.node_j < len(d) else 0.0
        ux_i = d[2 * elem.node_i + 1] if 2 * elem.node_i + 1 < len(d) else 0.0
        ux_j = d[2 * elem.node_j + 1] if 2 * elem.node_j + 1 < len(d) else 0.0

        ll = elem.length_m
        if ll < 1e-12:
            element_stresses.append(
                ElementStress(
                    element_id=elem.element_id,
                    axial_stress_pa=0.0,
                    bending_stress_pa=0.0,
                    von_mises_pa=0.0,
                    safety_factor=float("inf"),
                )
            )
            continue

        axial_strain = (uz_j - uz_i) / ll
        axial_stress = elem.elastic_modulus_pa * axial_strain

        # Bending: curvature approximation
        transverse_delta = ux_j - ux_i
        r_outer = math.sqrt(max(elem.area_m2, 0.0) / math.pi) if elem.area_m2 > 0 else 0.0
        curvature = transverse_delta / (ll**2) if ll > 1e-12 else 0.0
        bending_stress = elem.elastic_modulus_pa * curvature * r_outer

        # Von Mises stress (combined axial + bending, uniaxial formulation)
        sigma_a = axial_stress
        sigma_b = bending_stress
        von_mises = math.sqrt(sigma_a**2 + sigma_b**2 + sigma_a * sigma_b)

        sf = yield_stress_pa / max(von_mises, 1e-12)
        max_vm = max(max_vm, von_mises)

        # Strain energy for this element
        axial_energy = 0.5 * elem.area_m2 * ll * axial_stress * axial_strain
        total_strain_energy += abs(axial_energy)

        element_stresses.append(
            ElementStress(
                element_id=elem.element_id,
                axial_stress_pa=axial_stress,
                bending_stress_pa=bending_stress,
                von_mises_pa=von_mises,
                safety_factor=sf,
            )
        )

    return FEAResult(
        converged=True,
        nodal_displacements=nodal_displacements,
        element_stresses=element_stresses,
        max_displacement_m=max_disp,
        max_von_mises_pa=max_vm,
        total_strain_energy_j=total_strain_energy,
    )


def _solve_linear_system(a: List[List[float]], b: List[float]) -> List[float]:
    """Solve Ax = b using Gaussian elimination with partial pivoting."""
    n = len(b)
    # Augmented matrix
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]

    for col in range(n):
        # Partial pivoting
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]

        pivot = aug[col][col]
        if abs(pivot) < 1e-12:
            continue

        for row in range(col + 1, n):
            factor = aug[row][col] / pivot
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]

    # Back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        if abs(aug[i][i]) < 1e-12:
            x[i] = 0.0
            continue
        x[i] = aug[i][n]
        for j in range(i + 1, n):
            x[i] -= aug[i][j] * x[j]
        x[i] /= aug[i][i]

    return x


def evaluate_design_fea(
    design: DesignSpec,
    tip_load_n: float = 10.0,
    n_elements: int = 10,
    elastic_modulus_pa: float = 2.0e9,
    yield_stress_pa: float = 250e6,
) -> FEAResult:
    """Run a full FEA evaluation on a design spec.

    Models the actuator as a cantilever beam fixed at the base with a
    transverse tip load. Returns displacement and stress results.
    """
    mesh = generate_beam_mesh(design, n_elements, elastic_modulus_pa)

    bcs = [
        BoundaryCondition(node_id=0, dof="uz", value=0.0),
        BoundaryCondition(node_id=0, dof="ux", value=0.0),
    ]

    loads = [
        PointLoad(node_id=mesh.node_count - 1, fx=tip_load_n),
    ]

    return solve_static(mesh, bcs, loads, yield_stress_pa)
