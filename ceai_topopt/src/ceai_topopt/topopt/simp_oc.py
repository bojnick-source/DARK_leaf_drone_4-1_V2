from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .elasticity2d import Material, Mesh2D, compliance_and_sensitivities
from .filters import apply_density_filter, chain_rule_grad_through_density_filter


@dataclass(frozen=True)
class OCParams:
    move: float = 0.2
    eta: float = 0.5
    l1: float = 0.0
    l2: float = 1e9
    tol: float = 1e-3
    max_bisect: int = 80


@dataclass(frozen=True)
class TopOptParams:
    volfrac: float
    penal: float
    rmin: float
    max_iter: int
    change_tol: float = 1e-3


def oc_update(x: np.ndarray, dfdx: np.ndarray, volfrac: float, oc: OCParams) -> np.ndarray:
    if not (0 < volfrac < 1):
        raise ValueError("volfrac must be in (0,1)")

    x = np.clip(x, 1e-9, 1.0)
    dfdx = np.asarray(dfdx, dtype=float)

    l1, l2 = oc.l1, oc.l2
    for _ in range(oc.max_bisect):
        lam = 0.5 * (l1 + l2)
        x_candidate = x * np.sqrt(np.maximum(1e-30, -dfdx / lam))
        x_new = np.clip(x_candidate, x - oc.move, x + oc.move)
        x_new = np.clip(x_new, 0.0, 1.0)

        if x_new.mean() > volfrac:
            l1 = lam
        else:
            l2 = lam

        if (l2 - l1) / (l2 + l1 + 1e-30) < oc.tol:
            break

    if 0 < oc.eta < 1:
        x_new = oc.eta * x_new + (1.0 - oc.eta) * x

    return x_new


def run_topopt(mesh: Mesh2D, mat: Material, F: np.ndarray, fixed_dofs: np.ndarray,
              topo: TopOptParams, H, x0: np.ndarray | None = None, solver_cfg=None) -> dict:
    nelx, nely = mesh.nelx, mesh.nely
    if x0 is None:
        x = np.full((nely, nelx), topo.volfrac, dtype=float)
    else:
        if x0.shape != (nely, nelx):
            raise ValueError("x0 has wrong shape")
        x = np.clip(x0.astype(float), 0.0, 1.0)

    oc = OCParams()
    history = []

    for it in range(1, topo.max_iter + 1):
        x_phys = apply_density_filter(H, x)

        c, dc_dphys, _, solve_diag = compliance_and_sensitivities(
            mesh=mesh,
            x_phys=x_phys,
            penal=topo.penal,
            mat=mat,
            F=F,
            fixed_dofs=fixed_dofs,
            solver_cfg=solver_cfg,
        )

        dc_dx = chain_rule_grad_through_density_filter(H, dc_dphys)

        x_new = oc_update(x, dc_dx, topo.volfrac, oc)
        change = float(np.max(np.abs(x_new - x)))
        x = x_new

        history.append({
            "iter": it,
            "compliance": float(c),
            "vol_design": float(x.mean()),
            "vol_phys": float(apply_density_filter(H, x).mean()),
            "change": change,
            "solve": solve_diag,
        })

        if change < topo.change_tol:
            break

    return {"x": x, "x_phys": apply_density_filter(H, x), "history": history}
