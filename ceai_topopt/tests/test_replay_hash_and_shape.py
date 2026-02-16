from __future__ import annotations

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")

import json

import numpy as np
import pytest

from ceai_topopt.manifest import RunManifest, hash_outputs, utc_now_iso, write_manifest
from ceai_topopt.topopt.elasticity2d import Material, Mesh2D, compliance_and_sensitivities
from ceai_topopt.topopt.filters import density_filter_matrix
from ceai_topopt.topopt.problem_spec import build_problem, save_problem_artifacts
from ceai_topopt.topopt.replay import replay_compliance
from ceai_topopt.topopt.simp_oc import TopOptParams, run_topopt
from ceai_topopt.topopt.solver import SolverConfig


def _make_run(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    cfg = {
        "mesh": {"nelx": 30, "nely": 10},
        "material": {"E0": 1.0, "Emin": 1e-9, "nu": 0.3},
        "solver": {"solver": "direct", "compute_residual": True},
        "problem": {"type": "mbb"},
        "topopt": {"volfrac": 0.4, "penal": 3.0, "rmin": 2.0, "max_iter": 10, "change_tol": 1e-3},
    }

    mesh = Mesh2D(nelx=cfg["mesh"]["nelx"], nely=cfg["mesh"]["nely"])
    mat = Material(E0=1.0, Emin=1e-9, nu=0.3)
    solver_cfg = SolverConfig(solver="direct", compute_residual=True)

    F, fixed, resolved = build_problem(mesh, cfg["problem"])
    prob_paths = save_problem_artifacts(str(run_dir), F, fixed, resolved)

    H = density_filter_matrix(nely=mesh.nely, nelx=mesh.nelx, rmin=2.0)
    topo = TopOptParams(volfrac=0.4, penal=3.0, rmin=2.0, max_iter=10, change_tol=1e-3)
    res = run_topopt(
        mesh=mesh, mat=mat, F=F, fixed_dofs=fixed, topo=topo, H=H, solver_cfg=solver_cfg
    )

    np.save(run_dir / "x_phys.npy", res["x_phys"])
    c, _, _, _ = compliance_and_sensitivities(
        mesh, res["x_phys"], 3.0, mat, F, fixed, solver_cfg=solver_cfg
    )
    assert np.isfinite(c)

    out_paths = {"x_phys.npy": str(run_dir / "x_phys.npy"), **prob_paths}
    out_hashed = hash_outputs(out_paths)

    man = RunManifest(
        schema_version=2,
        run_id="TEST",
        created_at=utc_now_iso(),
        command="pytest",
        config=cfg,
        environment={},
        outputs=out_hashed,
    )
    write_manifest(str(run_dir / "manifest.json"), man)
    return run_dir


def test_replay_ok(tmp_path):
    run_dir = _make_run(tmp_path)
    rep = replay_compliance(str(run_dir))
    assert "compliance" in rep and np.isfinite(rep["compliance"])


def test_replay_hash_mismatch_fails(tmp_path):
    run_dir = _make_run(tmp_path)
    # corrupt x_phys.npy
    x = np.load(run_dir / "x_phys.npy")
    x[0, 0] = 0.123456
    np.save(run_dir / "x_phys.npy", x)
    with pytest.raises(ValueError):
        replay_compliance(str(run_dir))


def test_replay_shape_mismatch_fails(tmp_path):
    run_dir = _make_run(tmp_path)
    # rewrite manifest to match new hash of a wrong-shaped x_phys.npy (should fail on shape)
    x = np.load(run_dir / "x_phys.npy")
    x_bad = x[:5, :5]
    np.save(run_dir / "x_phys.npy", x_bad)

    man = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    sha256_func = __import__(
        "ceai_topopt.manifest", fromlist=["sha256_file"]
    ).sha256_file
    man["outputs"]["x_phys.npy"]["sha256"] = sha256_func(
        str(run_dir / "x_phys.npy")
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(man, indent=2) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError):
        replay_compliance(str(run_dir))
