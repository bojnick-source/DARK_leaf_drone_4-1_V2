from __future__ import annotations

import json
import os
from typing import Any

import numpy as np

from ..manifest import sha256_file
from .elasticity2d import Material, Mesh2D, compliance_and_sensitivities
from .solver import SolverConfig


def _verify_manifest_outputs(man: dict[str, Any]) -> dict[str, dict[str, str]]:
    if int(man.get("schema_version", 0)) < 2:
        raise ValueError("manifest schema_version < 2 (hashes required)")
    outs = man.get("outputs")
    if not isinstance(outs, dict):
        raise ValueError("manifest.outputs missing/invalid")
    for k, v in outs.items():
        if not (isinstance(v, dict) and "path" in v and "sha256" in v):
            raise ValueError(f"manifest.outputs[{k}] invalid")
        p = str(v["path"])
        h = str(v["sha256"])
        if not os.path.exists(p):
            raise FileNotFoundError(p)
        hh = sha256_file(p)
        if hh != h:
            raise ValueError(f"hash mismatch for {k}: expected {h}, got {hh}")
    return outs  # type: ignore[return-value]


def replay_compliance(run_dir: str) -> dict[str, Any]:
    manifest_path = f"{run_dir}/manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        man = json.load(f)

    outs = _verify_manifest_outputs(man)
    cfg = man["config"]

    nelx = int(cfg["mesh"]["nelx"])
    nely = int(cfg["mesh"]["nely"])
    penal = float(cfg["topopt"]["penal"])

    mat = Material(
        E0=float(cfg["material"].get("E0", 1.0)),
        Emin=float(cfg["material"].get("Emin", 1e-9)),
        nu=float(cfg["material"].get("nu", 0.3)),
    )

    solver_block = cfg.get("solver", {}) or {}
    solver_cfg = SolverConfig(
        solver=str(solver_block.get("solver", "auto")).lower(),
        cg_tol=float(solver_block.get("cg_tol", 1e-10)),
        cg_maxiter=int(solver_block.get("cg_maxiter", 2000)),
        ilu_drop_tol=float(solver_block.get("ilu_drop_tol", 1e-4)),
        ilu_fill_factor=float(solver_block.get("ilu_fill_factor", 20.0)),
        compute_residual=bool(solver_block.get("compute_residual", True)),
    )

    mesh = Mesh2D(nelx=nelx, nely=nely)
    ndof = mesh.ndof

    def _load_npy(key: str) -> np.ndarray:
        return np.load(str(outs[key]["path"]))

    x_phys = _load_npy("x_phys.npy").astype(float)
    F = _load_npy("F.npy").astype(float)
    fixed = _load_npy("fixed_dofs.npy").astype(int)

    if x_phys.shape != (nely, nelx):
        raise ValueError(f"x_phys shape {x_phys.shape} != ({nely},{nelx})")
    if F.shape != (ndof,):
        raise ValueError(f"F shape {F.shape} != ({ndof},)")
    if fixed.ndim != 1:
        raise ValueError("fixed_dofs must be 1D")
    if fixed.size == 0:
        raise ValueError("fixed_dofs empty")
    if int(fixed.min()) < 0 or int(fixed.max()) >= ndof:
        raise ValueError("fixed_dofs out of range")

    c, _, _, solve_diag = compliance_and_sensitivities(
        mesh=mesh,
        x_phys=x_phys,
        penal=penal,
        mat=mat,
        F=F,
        fixed_dofs=fixed,
        solver_cfg=solver_cfg,
    )
    return {"compliance": float(c), "solve": solve_diag}
