from __future__ import annotations

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")

import numpy as np
from ceai_topopt.topopt.elasticity2d import Material, Mesh2D, compliance_and_sensitivities
from ceai_topopt.topopt.examples import mbb_beam
from ceai_topopt.topopt.filters import apply_density_filter, density_filter_matrix
from ceai_topopt.topopt.simp_oc import TopOptParams, run_topopt


def test_mbb_regression_envelope():
    mesh = Mesh2D(nelx=60, nely=20)
    mat = Material(E0=1.0, Emin=1e-9, nu=0.3)
    bc = mbb_beam(mesh)
    H = density_filter_matrix(nely=mesh.nely, nelx=mesh.nelx, rmin=2.0)

    topo = TopOptParams(volfrac=0.40, penal=3.0, rmin=2.0, max_iter=60, change_tol=1e-3)

    x0 = np.full((mesh.nely, mesh.nelx), topo.volfrac, dtype=float)
    c0, _, _, _ = compliance_and_sensitivities(
        mesh, apply_density_filter(H, x0), topo.penal, mat, bc.F, bc.fixed_dofs
    )

    res = run_topopt(
        mesh=mesh, mat=mat, F=bc.F, fixed_dofs=bc.fixed_dofs, topo=topo, H=H, x0=None
    )

    c_final, _, _, _ = compliance_and_sensitivities(
        mesh, res["x_phys"], topo.penal, mat, bc.F, bc.fixed_dofs
    )

    c0 = float(c0)
    c_final = float(c_final)

    assert c_final < 0.85 * c0, {"c0": c0, "c_final": c_final}

    vol_phys = float(res["x_phys"].mean())
    assert abs(vol_phys - topo.volfrac) < 0.03, {"vol_phys": vol_phys, "target": topo.volfrac}

    assert 10.0 < c_final < 200.0, {"c_final": c_final}
