from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, TypedDict, cast

import numpy as np

from .elasticity2d import Mesh2D

DOF = Literal["ux", "uy"]


class FixedSpec(TypedDict, total=False):
    selector: str
    node: list[int]
    dofs: list[DOF]


class LoadSpec(TypedDict, total=False):
    selector: str
    node: list[int]
    fx: float
    fy: float


class ProblemCfg(TypedDict, total=False):
    type: str
    fixed: list[FixedSpec]
    loads: list[LoadSpec]


@dataclass(frozen=True)
class ProblemResolved:
    kind: str
    ndof: int
    fixed_dofs: list[int]
    loads: list[dict[str, Any]]


_DOF_MAP: dict[str, int] = {"ux": 0, "uy": 1}


def _require_keys(d: dict[str, Any], allowed: set[str], where: str) -> None:
    extra = set(d.keys()) - allowed
    if extra:
        raise ValueError(f"{where}: unknown keys: {sorted(extra)}")


def _as_int_pair(node: Any, where: str) -> tuple[int, int]:
    if not (isinstance(node, (list, tuple)) and len(node) == 2):
        raise ValueError(f"{where}: node must be [x,y]")
    x, y = node
    if not (isinstance(x, int) and isinstance(y, int)):
        raise ValueError(f"{where}: node coords must be int")
    return x, y


def _node_id(mesh: Mesh2D, x: int, y: int) -> int:
    if not (0 <= x <= mesh.nelx and 0 <= y <= mesh.nely):
        raise ValueError(f"node out of range: ({x},{y})")
    return y * mesh.nnx + x


def _dof_index(node: int, dof: DOF) -> int:
    if dof not in ("ux", "uy"):
        raise ValueError(f"invalid dof: {dof}")
    return 2 * node + _DOF_MAP[dof]


def _select_node(mesh: Mesh2D, sel: str) -> tuple[int, int]:
    s = sel.lower()
    if s == "left_bottom":
        return (0, 0)
    if s == "left_top":
        return (0, mesh.nely)
    if s == "right_mid":
        return (mesh.nelx, mesh.nely // 2)
    if s == "right_top":
        return (mesh.nelx, mesh.nely)
    if s == "right_bottom":
        return (mesh.nelx, 0)
    raise ValueError(f"unknown selector: {sel}")


def _builtin_mbb(mesh: Mesh2D) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    ndof = mesh.ndof
    F = np.zeros(ndof, dtype=float)

    x, y = _select_node(mesh, "right_mid")
    n_load = _node_id(mesh, x, y)
    dof_load = _dof_index(n_load, "uy")
    F[dof_load] = -1.0

    n_lb = _node_id(mesh, *_select_node(mesh, "left_bottom"))
    n_lt = _node_id(mesh, *_select_node(mesh, "left_top"))
    fixed = sorted({ _dof_index(n_lb, "ux"), _dof_index(n_lb, "uy"), _dof_index(n_lt, "ux") })
    fixed_dofs = np.array(fixed, dtype=int)

    resolved = ProblemResolved(
        kind="mbb",
        ndof=ndof,
        fixed_dofs=fixed,
        loads=[{"dof": int(dof_load), "value": -1.0, "selector": "right_mid", "dof_name": "uy"}],
    )
    return F, fixed_dofs, {
        "kind": resolved.kind,
        "ndof": resolved.ndof,
        "fixed_dofs": resolved.fixed_dofs,
        "loads": resolved.loads,
    }


def _explicit(mesh: Mesh2D, cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    _require_keys(cfg, {"type", "fixed", "loads"}, "problem")
    fixed_list = cfg.get("fixed", [])
    loads_list = cfg.get("loads", [])
    if not isinstance(fixed_list, list) or not isinstance(loads_list, list):
        raise ValueError("problem: fixed and loads must be lists")

    ndof = mesh.ndof
    F = np.zeros(ndof, dtype=float)
    fixed_set: set[int] = set()
    loads: list[dict[str, Any]] = []

    for i, item_any in enumerate(fixed_list):
        if not isinstance(item_any, dict):
            raise ValueError(f"problem.fixed[{i}]: must be dict")
        item = cast(dict[str, Any], item_any)
        _require_keys(item, {"selector", "node", "dofs"}, f"problem.fixed[{i}]")
        if "selector" in item:
            if "node" in item:
                raise ValueError(f"problem.fixed[{i}]: provide selector OR node, not both")
            x, y = _select_node(mesh, str(item["selector"]))
        else:
            if "node" not in item:
                raise ValueError(f"problem.fixed[{i}]: missing node/selector")
            x, y = _as_int_pair(item["node"], f"problem.fixed[{i}]")
        dofs = item.get("dofs")
        if not (isinstance(dofs, list) and len(dofs) >= 1):
            raise ValueError(f"problem.fixed[{i}]: dofs must be non-empty list")
        n = _node_id(mesh, x, y)
        for d in dofs:
            if not isinstance(d, str):
                raise ValueError(f"problem.fixed[{i}]: dof must be string")
            dl = d.lower()
            if dl not in _DOF_MAP:
                raise ValueError(f"problem.fixed[{i}]: invalid dof: {d}")
            fixed_set.add(_dof_index(n, cast(DOF, dl)))

    for i, item_any in enumerate(loads_list):
        if not isinstance(item_any, dict):
            raise ValueError(f"problem.loads[{i}]: must be dict")
        item = cast(dict[str, Any], item_any)
        _require_keys(item, {"selector", "node", "fx", "fy"}, f"problem.loads[{i}]")
        if "selector" in item:
            if "node" in item:
                raise ValueError(f"problem.loads[{i}]: provide selector OR node, not both")
            x, y = _select_node(mesh, str(item["selector"]))
            sel = str(item["selector"])
        else:
            if "node" not in item:
                raise ValueError(f"problem.loads[{i}]: missing node/selector")
            x, y = _as_int_pair(item["node"], f"problem.loads[{i}]")
            sel = None
        fx = float(item.get("fx", 0.0))
        fy = float(item.get("fy", 0.0))
        if fx == 0.0 and fy == 0.0:
            raise ValueError(f"problem.loads[{i}]: fx and fy both zero")
        n = _node_id(mesh, x, y)
        if fx != 0.0:
            dof = _dof_index(n, "ux")
            F[dof] += fx
            loads.append({"dof": int(dof), "value": fx, "node": [x, y], "selector": sel, "dof_name": "ux"})
        if fy != 0.0:
            dof = _dof_index(n, "uy")
            F[dof] += fy
            loads.append({"dof": int(dof), "value": fy, "node": [x, y], "selector": sel, "dof_name": "uy"})

    fixed = sorted(fixed_set)
    if not fixed:
        raise ValueError("problem.explicit: fixed dofs empty")

    resolved = ProblemResolved(kind="explicit", ndof=ndof, fixed_dofs=fixed, loads=loads)
    return F, np.array(fixed, dtype=int), {
        "kind": resolved.kind,
        "ndof": resolved.ndof,
        "fixed_dofs": resolved.fixed_dofs,
        "loads": resolved.loads,
    }


def build_problem(mesh: Mesh2D, cfg_any: dict[str, Any] | None) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    cfg = cfg_any or {"type": "mbb"}
    if not isinstance(cfg, dict):
        raise ValueError("problem must be a dict")
    t = str(cfg.get("type", "mbb")).lower()
    if t == "mbb":
        return _builtin_mbb(mesh)
    if t == "explicit":
        return _explicit(mesh, cfg)
    raise ValueError(f"unknown problem type: {t}")


def save_problem_artifacts(run_dir: str, F: np.ndarray, fixed_dofs: np.ndarray, resolved: dict[str, Any]) -> dict[str, str]:
    import os
    os.makedirs(run_dir, exist_ok=True)
    fF = f"{run_dir}/F.npy"
    ffix = f"{run_dir}/fixed_dofs.npy"
    fres = f"{run_dir}/problem_resolved.json"
    np.save(fF, F.astype(float))
    np.save(ffix, fixed_dofs.astype(int))
    with open(fres, "w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2)
        f.write("\n")
    return {"F.npy": fF, "fixed_dofs.npy": ffix, "problem_resolved.json": fres}
