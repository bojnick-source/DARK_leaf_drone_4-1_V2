from __future__ import annotations

import pytest
pytest.importorskip("numpy")
pytest.importorskip("scipy")

from ceai_topopt.topopt.elasticity2d import Mesh2D
from ceai_topopt.topopt.problem_spec import build_problem


def test_explicit_unknown_dof_fails():
    mesh = Mesh2D(nelx=10, nely=4)
    with pytest.raises(ValueError):
        build_problem(mesh, {"type": "explicit", "fixed": [{"node": [0, 0], "dofs": ["uz"]}], "loads": [{"node": [10, 2], "fy": -1.0}]})


def test_explicit_out_of_range_node_fails():
    mesh = Mesh2D(nelx=10, nely=4)
    with pytest.raises(ValueError):
        build_problem(mesh, {"type": "explicit", "fixed": [{"node": [999, 0], "dofs": ["ux"]}], "loads": [{"node": [10, 2], "fy": -1.0}]})


def test_explicit_zero_load_fails():
    mesh = Mesh2D(nelx=10, nely=4)
    with pytest.raises(ValueError):
        build_problem(mesh, {"type": "explicit", "fixed": [{"node": [0, 0], "dofs": ["ux"]}], "loads": [{"node": [10, 2], "fx": 0.0, "fy": 0.0}]})
