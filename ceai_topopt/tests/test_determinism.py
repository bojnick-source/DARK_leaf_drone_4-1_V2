from __future__ import annotations

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")

import numpy as np
from ceai_topopt.topopt.elasticity2d import Material, Mesh2D, compliance_and_sensitivities
from ceai_topopt.topopt.examples import mbb_beam
from ceai_topopt.topopt.filters import density_filter_matrix
from ceai_topopt.topopt.simp_oc import TopOptParams, run_topopt


def _run_once():
    mesh = Mesh2D(nelx=30, nely=10)
    mat = Material(E0=1.0, Emin=1e-9, nu=0.3)
    bc = mbb_beam(mesh)
    H = density_filter_matrix(nely=mesh.nely, nelx=mesh.nelx, rmin=2.0)

    topo = TopOptParams(volfrac=0.40, penal=3.0, rmin=2.0, max_iter=35, change_tol=1e-3)

    res = run_topopt(mesh=mesh, mat=mat, F=bc.F, fixed_dofs=bc.fixed_dofs, topo=topo, H=H, x0=None)

    c_final, _, _, _ = compliance_and_sensitivities(
        mesh, res["x_phys"], topo.penal, mat, bc.F, bc.fixed_dofs
    )
    return res["x"], res["x_phys"], float(c_final), res["history"]


def test_exact_repeatability():
    x1, xphys1, c1, h1 = _run_once()
    x2, xphys2, c2, h2 = _run_once()

    assert np.array_equal(x1, x2)
    assert np.array_equal(xphys1, xphys2)
    assert c1 == c2
    assert h1 == h2
