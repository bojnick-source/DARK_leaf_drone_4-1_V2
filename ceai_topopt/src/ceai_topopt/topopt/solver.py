from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

SolverType = Literal["direct", "cg", "auto"]


@dataclass(frozen=True)
class SolverConfig:
    solver: SolverType = "auto"

    # CG parameters
    cg_tol: float = 1e-10
    cg_maxiter: int = 2000

    # ILU preconditioner parameters (used for CG as M^{-1})
    ilu_drop_tol: float = 1e-4
    ilu_fill_factor: float = 20.0

    # Diagnostics
    compute_residual: bool = True


@dataclass
class SolveInfo:
    solver_used: str
    converged: bool
    iterations: int | None
    residual_l2: float | None
    note: str | None = None


def _residual_norm(K: sp.spmatrix, u: np.ndarray, f: np.ndarray) -> float:
    r = f - K @ u
    return float(np.linalg.norm(r))


def _direct_solve(K: sp.csr_matrix, f: np.ndarray) -> tuple[np.ndarray, SolveInfo]:
    u = spla.spsolve(K, f)
    if not np.all(np.isfinite(u)):
        return u, SolveInfo(
            solver_used="direct",
            converged=False,
            iterations=None,
            residual_l2=None,
            note="non-finite solution",
        )
    return u, SolveInfo(
        solver_used="direct",
        converged=True,
        iterations=None,
        residual_l2=None,
        note=None,
    )


def _build_ilu_preconditioner(K: sp.csr_matrix, cfg: SolverConfig) -> spla.LinearOperator:
    # spilu requires CSC
    Kc = K.tocsc()
    ilu = spla.spilu(Kc, drop_tol=cfg.ilu_drop_tol, fill_factor=cfg.ilu_fill_factor)

    def mvp(x: np.ndarray) -> np.ndarray:
        return ilu.solve(x)

    return spla.LinearOperator(shape=K.shape, matvec=mvp, dtype=np.float64)


def _cg_solve(K: sp.csr_matrix, f: np.ndarray, cfg: SolverConfig) -> tuple[np.ndarray, SolveInfo]:
    # CG expects SPD. Kff should be SPD for linear elasticity with proper constraints.
    # We still guard and report.
    it_counter = {"k": 0}

    def _cb(_xk):
        it_counter["k"] += 1

    # Preconditioner (ILU)
    M = _build_ilu_preconditioner(K, cfg)

    u, info = spla.cg(K, f, tol=cfg.cg_tol, maxiter=cfg.cg_maxiter, M=M, callback=_cb)

    # scipy: info = 0 success, >0 iter limit, <0 breakdown
    if info == 0 and np.all(np.isfinite(u)):
        return u, SolveInfo(
            solver_used="cg",
            converged=True,
            iterations=it_counter["k"],
            residual_l2=None,
            note=None,
        )
    note = "cg did not converge" if info > 0 else "cg breakdown"
    if not np.all(np.isfinite(u)):
        note = (note + "; non-finite solution") if note else "non-finite solution"
    return u, SolveInfo(
        solver_used="cg",
        converged=False,
        iterations=it_counter["k"],
        residual_l2=None,
        note=note,
    )


def solve_linear_system(
    K: sp.csr_matrix,
    f: np.ndarray,
    cfg: SolverConfig,
) -> tuple[np.ndarray, SolveInfo]:
    """
    Robust solve with optional auto-fallback.
    """
    if cfg.solver not in ("direct", "cg", "auto"):
        raise ValueError(f"Unknown solver type: {cfg.solver}")

    # Direct only
    if cfg.solver == "direct":
        u, info = _direct_solve(K, f)
        if cfg.compute_residual and info.converged:
            info.residual_l2 = _residual_norm(K, u, f)
        return u, info

    # CG only
    if cfg.solver == "cg":
        u, info = _cg_solve(K, f, cfg)
        if cfg.compute_residual:
            info.residual_l2 = _residual_norm(K, u, f)
        return u, info

    # Auto: try direct then fallback to CG
    u, info = _direct_solve(K, f)
    if info.converged:
        if cfg.compute_residual:
            info.residual_l2 = _residual_norm(K, u, f)
        return u, info

    # fallback
    u2, info2 = _cg_solve(K, f, cfg)
    if cfg.compute_residual:
        info2.residual_l2 = _residual_norm(K, u2, f)

    # If fallback also fails: hard fail (stop-ship)
    if not info2.converged:
        raise RuntimeError(
            f"Solver failed: direct({info.note}) then cg({info2.note}), "
            f"residual={info2.residual_l2}"
        )

    info2.note = f"auto fallback: direct failed ({info.note})"
    return u2, info2
