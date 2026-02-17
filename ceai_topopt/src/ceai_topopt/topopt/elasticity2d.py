from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp


@dataclass(frozen=True)
class Material:
    E0: float = 1.0
    Emin: float = 1e-9
    nu: float = 0.3


@dataclass(frozen=True)
class Mesh2D:
    nelx: int
    nely: int

    @property
    def nnx(self) -> int:
        return self.nelx + 1

    @property
    def nny(self) -> int:
        return self.nely + 1

    @property
    def nnodes(self) -> int:
        return self.nnx * self.nny

    @property
    def ndof(self) -> int:
        return 2 * self.nnodes


def lk_plane_stress(E: float, nu: float) -> np.ndarray:
    """
    4-node quad (Q4) element stiffness matrix (8x8), plane stress, unit thickness.
    Standard matrix used in topology optimization literature.
    """
    k = np.array(
        [
            [
                1 / 2 - nu / 6,
                1 / 8 + nu / 8,
                -1 / 4 - nu / 12,
                -1 / 8 + 3 * nu / 8,
                -1 / 4 + nu / 12,
                -1 / 8 - nu / 8,
                nu / 6,
                1 / 8 - 3 * nu / 8,
            ],
            [
                1 / 8 + nu / 8,
                1 / 2 - nu / 6,
                1 / 8 - 3 * nu / 8,
                nu / 6,
                -1 / 8 - nu / 8,
                -1 / 4 + nu / 12,
                -1 / 8 + 3 * nu / 8,
                -1 / 4 - nu / 12,
            ],
            [
                -1 / 4 - nu / 12,
                1 / 8 - 3 * nu / 8,
                1 / 2 - nu / 6,
                -1 / 8 - nu / 8,
                nu / 6,
                -1 / 8 + 3 * nu / 8,
                -1 / 4 + nu / 12,
                1 / 8 + nu / 8,
            ],
            [
                -1 / 8 + 3 * nu / 8,
                nu / 6,
                -1 / 8 - nu / 8,
                1 / 2 - nu / 6,
                1 / 8 - 3 * nu / 8,
                -1 / 4 - nu / 12,
                1 / 8 + nu / 8,
                -1 / 4 + nu / 12,
            ],
            [
                -1 / 4 + nu / 12,
                -1 / 8 - nu / 8,
                nu / 6,
                1 / 8 - 3 * nu / 8,
                1 / 2 - nu / 6,
                1 / 8 + nu / 8,
                -1 / 4 - nu / 12,
                -1 / 8 + 3 * nu / 8,
            ],
            [
                -1 / 8 - nu / 8,
                -1 / 4 + nu / 12,
                -1 / 8 + 3 * nu / 8,
                -1 / 4 - nu / 12,
                1 / 8 + nu / 8,
                1 / 2 - nu / 6,
                1 / 8 - 3 * nu / 8,
                nu / 6,
            ],
            [
                nu / 6,
                -1 / 8 + 3 * nu / 8,
                -1 / 4 + nu / 12,
                1 / 8 + nu / 8,
                -1 / 4 - nu / 12,
                1 / 8 - 3 * nu / 8,
                1 / 2 - nu / 6,
                -1 / 8 - nu / 8,
            ],
            [
                1 / 8 - 3 * nu / 8,
                -1 / 4 - nu / 12,
                1 / 8 + nu / 8,
                -1 / 4 + nu / 12,
                -1 / 8 + 3 * nu / 8,
                nu / 6,
                -1 / 8 - nu / 8,
                1 / 2 - nu / 6,
            ],
        ],
        dtype=float,
    )
    return (E / (1.0 - nu**2)) * k


def edof_matrix(mesh: Mesh2D) -> np.ndarray:
    """
    Element DOF connectivity: shape (nelx*nely, 8)
    Flattening convention for elements: x-major, y-minor, but we keep it consistent everywhere by
    reshaping with order='F' on (nely, nelx) fields.
    """
    nelx, nely = mesh.nelx, mesh.nely
    nnx = mesh.nnx

    edof = np.zeros((nelx * nely, 8), dtype=int)
    e = 0
    for x in range(nelx):
        for y in range(nely):
            n1 = y * nnx + x
            n2 = y * nnx + (x + 1)
            n3 = (y + 1) * nnx + (x + 1)
            n4 = (y + 1) * nnx + x
            edof[e, :] = np.array([2*n1, 2*n1+1, 2*n2, 2*n2+1, 2*n3, 2*n3+1, 2*n4, 2*n4+1])
            e += 1
    return edof


def assemble_global_K(
    mesh: Mesh2D, x_phys: np.ndarray, penal: float, mat: Material
) -> tuple[sp.csr_matrix, np.ndarray]:
    nelx, nely = mesh.nelx, mesh.nely
    if x_phys.shape != (nely, nelx):
        raise ValueError(f"x_phys must be shape ({nely},{nelx}), got {x_phys.shape}")

    ke = lk_plane_stress(1.0, mat.nu)  # normalized; density interpolation applies E scaling
    edof = edof_matrix(mesh)

    iK = np.kron(edof, np.ones((8, 1), dtype=int)).ravel()
    jK = np.kron(edof, np.ones((1, 8), dtype=int)).ravel()

    x_flat = x_phys.reshape(-1, order="F")
    Ee = mat.Emin + (mat.E0 - mat.Emin) * (x_flat ** penal)
    sK = (ke.ravel()[None, :] * Ee[:, None]).ravel()

    K = sp.coo_matrix((sK, (iK, jK)), shape=(mesh.ndof, mesh.ndof)).tocsr()
    K = (K + K.T) * 0.5
    return K, ke


def solve_displacements(
    K: sp.csr_matrix,
    F: np.ndarray,
    fixed_dofs: np.ndarray,
    solver_cfg=None,
):
    """
    Solve KU=F with fixed_dofs clamped to zero, using robust solver strategy.

    Returns U plus a diagnostics dict.
    """
    from .solver import SolverConfig, solve_linear_system  # local import to avoid circular deps

    cfg = solver_cfg if solver_cfg is not None else SolverConfig()

    ndof = K.shape[0]
    if F.shape != (ndof,):
        raise ValueError(f"F must be shape ({ndof},), got {F.shape}")

    fixed = np.array(fixed_dofs, dtype=int).ravel()
    if fixed.size == 0:
        raise ValueError("fixed_dofs is empty; elasticity stiffness matrix will be singular.")

    all_dofs = np.arange(ndof, dtype=int)
    free = np.setdiff1d(all_dofs, fixed, assume_unique=False)

    Kff = K[free][:, free]
    Ff = F[free]

    Uf, info = solve_linear_system(Kff, Ff, cfg)

    U = np.zeros(ndof, dtype=float)
    U[free] = Uf
    U[fixed] = 0.0

    diag = {
        "solver_used": info.solver_used,
        "converged": bool(info.converged),
        "iterations": info.iterations,
        "residual_l2": info.residual_l2,
        "note": info.note,
    }
    return U, diag


def compliance_and_sensitivities(
    mesh: Mesh2D,
    x_phys: np.ndarray,
    penal: float,
    mat: Material,
    F: np.ndarray,
    fixed_dofs: np.ndarray,
    solver_cfg=None,
) -> tuple[float, np.ndarray, np.ndarray, dict]:
    """
    Returns: compliance c, dc/dx_phys (nely,nelx), displacement vector U.
    """
    K, ke = assemble_global_K(mesh, x_phys, penal, mat)
    U, solve_diag = solve_displacements(K, F, fixed_dofs, solver_cfg=solver_cfg)

    c = float(F @ U)

    edof = edof_matrix(mesh)
    Ue = U[edof]  # (ne,8)
    ce = np.einsum("...i,ij,...j->...", Ue, ke, Ue)  # per-element energy

    x_flat = x_phys.reshape(-1, order="F")
    dE_dx = (mat.E0 - mat.Emin) * penal * (x_flat ** (penal - 1.0))
    dc = -(dE_dx * ce)
    dc = dc.reshape((mesh.nely, mesh.nelx), order="F")
    return c, dc, U, solve_diag
