from __future__ import annotations

import numpy as np

from .elasticity2d import Mesh2D, Material, compliance_and_sensitivities
from .filters import density_filter_matrix, apply_density_filter, chain_rule_grad_through_density_filter
from .examples import mbb_beam


def gradcheck_compliance(
    nelx: int = 30,
    nely: int = 10,
    volfrac: float = 0.4,
    penal: float = 3.0,
    rmin: float = 2.0,
    eps: float = 1e-6,
    samples: int = 25,
    seed: int = 0,
) -> dict:
    rng = np.random.default_rng(seed)
    mesh = Mesh2D(nelx=nelx, nely=nely)
    mat = Material(E0=1.0, Emin=1e-9, nu=0.3)
    bc = mbb_beam(mesh)

    x = np.clip(volfrac + 0.05 * rng.standard_normal((nely, nelx)), 0.05, 0.95)
    H = density_filter_matrix(nely=nely, nelx=nelx, rmin=rmin)

    x_phys = apply_density_filter(H, x)
    c0, dc_dphys, _, _solve = compliance_and_sensitivities(mesh, x_phys, penal, mat, bc.F, bc.fixed_dofs)
    dc_dx = chain_rule_grad_through_density_filter(H, dc_dphys)

    idxs = [(int(rng.integers(0, nely)), int(rng.integers(0, nelx))) for _ in range(samples)]

    rel_errors = []
    worst = None

    for (iy, ix) in idxs:
        x_p = x.copy()
        x_m = x.copy()
        x_p[iy, ix] = np.clip(x_p[iy, ix] + eps, 0.0, 1.0)
        x_m[iy, ix] = np.clip(x_m[iy, ix] - eps, 0.0, 1.0)

        c_p, _, _, _ = compliance_and_sensitivities(mesh, apply_density_filter(H, x_p), penal, mat, bc.F, bc.fixed_dofs)
        c_m, _, _, _ = compliance_and_sensitivities(mesh, apply_density_filter(H, x_m), penal, mat, bc.F, bc.fixed_dofs)

        fd = (c_p - c_m) / (2.0 * eps)
        an = dc_dx[iy, ix]

        denom = max(1e-9, abs(fd) + abs(an))
        rel = abs(fd - an) / denom
        rel_errors.append(rel)

        if worst is None or rel > worst["rel_error"]:
            worst = {"iy": iy, "ix": ix, "fd": float(fd), "analytic": float(an), "rel_error": float(rel)}

    rel_errors = np.array(rel_errors, dtype=float)
    return {
        "c0": float(c0),
        "samples": samples,
        "eps": eps,
        "rel_error_mean": float(rel_errors.mean()),
        "rel_error_p95": float(np.quantile(rel_errors, 0.95)),
        "rel_error_max": float(rel_errors.max()),
        "worst": worst,
    }
