from __future__ import annotations

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")

import numpy as np
from ceai_topopt.topopt.elasticity2d import Material, Mesh2D, compliance_and_sensitivities
from ceai_topopt.topopt.examples import mbb_beam
from ceai_topopt.topopt.filters import apply_density_filter, density_filter_matrix
from ceai_topopt.topopt.solver import SolverConfig


def test_direct_vs_cg_close_compliance():
    """
    STOP-SHIP: iterative solver must match direct solve within a sane tolerance for this benchmark.
    """
    mesh = Mesh2D(nelx=40, nely=12)
    mat = Material(E0=1.0, Emin=1e-9, nu=0.3)
    bc = mbb_beam(mesh)

    H = density_filter_matrix(nely=mesh.nely, nelx=mesh.nelx, rmin=2.0)
    x0 = np.full((mesh.nely, mesh.nelx), 0.4, dtype=float)
    x_phys = apply_density_filter(H, x0)

    c_d, _, _, diag_d = compliance_and_sensitivities(
        mesh, x_phys, 3.0, mat, bc.F, bc.fixed_dofs,
        solver_cfg=SolverConfig(solver="direct", compute_residual=True)
    )
    c_c, _, _, diag_c = compliance_and_sensitivities(
        mesh, x_phys, 3.0, mat, bc.F, bc.fixed_dofs,
        solver_cfg=SolverConfig(solver="cg", cg_tol=1e-10, cg_maxiter=2000, compute_residual=True)
    )

    assert diag_d["converged"] is True
    assert diag_c["converged"] is True
    # Compliance should be very close (numerical tolerance)
    assert abs(float(c_d) - float(c_c)) / max(1e-9, abs(float(c_d))) < 1e-6, {
        "c_direct": float(c_d), "c_cg": float(c_c), "diag_direct": diag_d, "diag_cg": diag_c
    }
