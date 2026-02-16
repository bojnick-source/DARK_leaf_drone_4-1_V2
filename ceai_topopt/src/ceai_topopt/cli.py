from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import typer
import yaml
from rich.console import Console
from rich.table import Table
import matplotlib.pyplot as plt

from .manifest import RunManifest, basic_environment, run_id, utc_now_iso, write_manifest, hash_outputs
from .topopt.elasticity2d import Mesh2D, Material, compliance_and_sensitivities
from .topopt.filters import density_filter_matrix
from .topopt.gradcheck import gradcheck_compliance
from .topopt.problem_spec import build_problem, save_problem_artifacts
from .topopt.replay import replay_compliance
from .topopt.simp_oc import TopOptParams, run_topopt
from .topopt.solver import SolverConfig

app = typer.Typer(add_completion=False)
console = Console()


def _save_density_image(path: str, x_phys: np.ndarray, title: str) -> None:
    plt.figure()
    plt.imshow(1.0 - x_phys, cmap="gray", origin="lower", interpolation="nearest")
    plt.title(title)
    plt.axis("off")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()


@app.command()
def gradcheck(
    nelx: int = typer.Option(30, "--nelx"),
    nely: int = typer.Option(10, "--nely"),
    volfrac: float = typer.Option(0.4, "--volfrac"),
    penal: float = typer.Option(3.0, "--penal"),
    rmin: float = typer.Option(2.0, "--rmin"),
    eps: float = typer.Option(1e-6, "--eps"),
    samples: int = typer.Option(25, "--samples"),
    seed: int = typer.Option(0, "--seed"),
    max_rel_error: float = typer.Option(2e-2, "--max-rel-error"),
) -> None:
    res = gradcheck_compliance(
        nelx=nelx, nely=nely, volfrac=volfrac, penal=penal,
        rmin=rmin, eps=eps, samples=samples, seed=seed
    )
    console.print(res)
    if res["rel_error_max"] > max_rel_error:
        console.print(f"[red]FAIL[/red] rel_error_max={res['rel_error_max']:.3e} > {max_rel_error:.3e}")
        raise typer.Exit(code=1)
    console.print(f"[green]PASS[/green] rel_error_max={res['rel_error_max']:.3e} <= {max_rel_error:.3e}")


@app.command()
def replay(
    run_dir: str = typer.Option(..., "--run-dir"),
) -> None:
    console.print(replay_compliance(run_dir))


@app.command()
def run(
    config: str = typer.Option(..., "--config"),
    out_dir: str = typer.Option("out", "--out"),
) -> None:
    with open(config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise typer.Exit(code=2)

    nelx = int(cfg["mesh"]["nelx"])
    nely = int(cfg["mesh"]["nely"])

    volfrac = float(cfg["topopt"]["volfrac"])
    penal = float(cfg["topopt"]["penal"])
    rmin = float(cfg["topopt"]["rmin"])
    max_iter = int(cfg["topopt"]["max_iter"])
    change_tol = float(cfg["topopt"].get("change_tol", 1e-3))

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

    rid = run_id()
    run_path = Path(out_dir) / rid
    run_path.mkdir(parents=True, exist_ok=True)

    mesh = Mesh2D(nelx=nelx, nely=nely)
    prob_cfg = cfg.get("problem", None)
    F, fixed_dofs, resolved = build_problem(mesh, prob_cfg)
    H = density_filter_matrix(nely=nely, nelx=nelx, rmin=rmin)

    topo = TopOptParams(volfrac=volfrac, penal=penal, rmin=rmin, max_iter=max_iter, change_tol=change_tol)
    res = run_topopt(mesh=mesh, mat=mat, F=F, fixed_dofs=fixed_dofs, topo=topo, H=H, x0=None, solver_cfg=solver_cfg)

    # artifacts
    np.save(run_path / "x.npy", res["x"])
    np.save(run_path / "x_phys.npy", res["x_phys"])
    with open(run_path / "history.json", "w", encoding="utf-8") as f:
        json.dump(res["history"], f, indent=2)
        f.write("\n")
    _save_density_image(str(run_path / "density.png"), res["x_phys"], "Density (filtered)")

    prob_paths = save_problem_artifacts(str(run_path), F, fixed_dofs, resolved)

    c_final, _, _, solve_diag = compliance_and_sensitivities(mesh, res["x_phys"], penal, mat, F, fixed_dofs, solver_cfg=solver_cfg)

    t = Table(title="TopOpt Summary (last 10 iters)")
    t.add_column("iter")
    t.add_column("compliance")
    t.add_column("vol_phys")
    t.add_column("change")
    t.add_column("solver")
    t.add_column("resid")

    for row in res["history"][-10:]:
        s = row.get("solve", {})
        t.add_row(
            str(row["iter"]),
            f"{row['compliance']:.6e}",
            f"{row['vol_phys']:.4f}",
            f"{row['change']:.3e}",
            str(s.get("solver_used")),
            f"{(s.get('residual_l2') if s.get('residual_l2') is not None else float('nan')):.3e}",
        )
    console.print(t)
    console.print(f"final_compliance={c_final:.6e} solve={solve_diag}")

    out_paths = {
        "x.npy": str(run_path / "x.npy"),
        "x_phys.npy": str(run_path / "x_phys.npy"),
        "history.json": str(run_path / "history.json"),
        "density.png": str(run_path / "density.png"),
        **prob_paths,
    }
    out_hashed = hash_outputs(out_paths)

    manifest = RunManifest(
        schema_version=2,
        run_id=rid,
        created_at=utc_now_iso(),
        command=f"ceai-topopt run --config {config} --out {out_dir}",
        config=cfg,
        environment=basic_environment(),
        outputs=out_hashed,
    )
    write_manifest(str(run_path / "manifest.json"), manifest)
    console.print(f"\n[green]DONE[/green] run_dir={run_path}")
