from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .elasticity2d import Mesh2D


@dataclass(frozen=True)
class LoadBC:
    F: np.ndarray
    fixed_dofs: np.ndarray


def mbb_beam(mesh: Mesh2D) -> LoadBC:
    """
    A stable MBB-style benchmark:
      - downward point load at mid-height right edge
      - constraints at left edge to eliminate rigid-body motion robustly
    """
    ndof = mesh.ndof
    F = np.zeros(ndof, dtype=float)

    def node_id(x: int, y: int) -> int:
        return y * mesh.nnx + x

    load_node = node_id(mesh.nelx, mesh.nely // 2)
    F[2 * load_node + 1] = -1.0

    left_bottom = node_id(0, 0)
    left_top = node_id(0, mesh.nely)

    fixed = {
        2 * left_bottom + 0,  # ux
        2 * left_bottom + 1,  # uy
        2 * left_top + 0,     # ux
    }

    fixed_dofs = np.array(sorted(fixed), dtype=int)
    return LoadBC(F=F, fixed_dofs=fixed_dofs)
