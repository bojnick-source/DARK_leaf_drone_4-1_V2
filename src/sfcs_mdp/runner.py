from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from sfcs_mdp.artifacts import (
    create_placeholder_dir,
    create_placeholder_file,
    expand_placeholders,
    normalize_optional_name,
    resolve_path,
    write_json,
    write_text,
    write_yaml,
)
from sfcs_mdp.hashutil import hash_files, sha256_bytes
from sfcs_mdp.model import BlockLevel, ProcessStep, StepType
from sfcs_mdp.validate import load_spec, topological_sort, validate_spec


@dataclass(frozen=True)
class RunConfig:
    spec_path: Path
    build_id: str
    rev_tag: str
    block_level: BlockLevel
    simulate: bool
    lot_id: str
    ncr_id: str
    repo_root: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _block_level_index(level: BlockLevel) -> int:
    order = list(BlockLevel)
    return order.index(level)


def _block_level_at_least(current: BlockLevel, required: BlockLevel) -> bool:
    return _block_level_index(current) >= _block_level_index(required)


def _build_placeholders(config: RunConfig) -> dict[str, str]:
    return {
        "build_id": config.build_id,
        "REV_TAG": config.rev_tag,
        "lot_id": config.lot_id,
        "ncr_id": config.ncr_id,
    }


def _compute_run_id(config: RunConfig, spec_text: str) -> str:
    seed_text = f"{config.build_id}:{config.rev_tag}:{config.block_level}:{config.simulate}"
    seed = seed_text.encode("utf-8")
    return sha256_bytes(spec_text.encode("utf-8") + seed)[:12]


def _log_event(log_file: Path, event: dict[str, Any]) -> None:
    line = json.dumps(event, sort_keys=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line)


def _build_dir(config: RunConfig) -> Path:
    return config.repo_root / "records" / "builds" / config.build_id


def _signoff_path(build_dir: Path, step_id: str) -> Path:
    return build_dir / "signoffs" / f"{step_id}.signed"


def _create_manifest(config: RunConfig, manifest_path: Path) -> dict[str, Any]:
    seed = sha256_bytes(f"{config.build_id}:{config.rev_tag}".encode("utf-8"))
    manifest = {
        "build_id": config.build_id,
        "block_level": config.block_level.value,
        "cad_rev": config.rev_tag,
        "afp_path_hash": seed[:16],
        "cure_profile_hash": seed[16:32],
        "materials_lot_ids": [config.lot_id],
        "insert_lot_ids": [config.lot_id],
        "operator_ids": ["OP_SIM"],
        "machine_ids": ["MFG_SIM"],
        "calibration_set_ids": ["CAL_SIM"],
        "environment_log": {"temp": "21C", "humidity": "45%"},
        "qc_gate_results": {},
    }
    write_json(manifest_path, manifest)
    return manifest


def _create_traveler(spec_data: dict[str, Any], path: Path) -> None:
    write_yaml(path, spec_data)


def _create_simulated_outputs(step: ProcessStep, config: RunConfig) -> None:
    placeholders = _build_placeholders(config)
    for output in step.outputs:
        expanded = expand_placeholders(output, placeholders)
        if expanded.endswith("acceptance_data_package.zip"):
            continue
        try:
            output_path = resolve_path(config.repo_root, expanded)
        except ValueError:
            continue
        if expanded.endswith("/"):
            create_placeholder_dir(output_path)
        elif output_path.suffix in {".json", ".yaml", ".yml"}:
            write_text(output_path, f"SIMULATED OUTPUT for {step.step_id}\n")
        else:
            create_placeholder_file(output_path, f"SIMULATED OUTPUT for {step.step_id}\n")

    for evidence in step.evidence.required:
        name, _ = normalize_optional_name(evidence)
        expanded_name = expand_placeholders(name, placeholders)
        try:
            evidence_path = resolve_path(_build_dir(config), expanded_name)
        except ValueError:
            continue
        if name.endswith("/"):
            create_placeholder_dir(evidence_path)
            create_placeholder_file(evidence_path / "placeholder.txt", "SIMULATED EVIDENCE\n")
        else:
            create_placeholder_file(evidence_path, "SIMULATED EVIDENCE\n")

    if step.acceptance.criteria:
        signoff = _signoff_path(_build_dir(config), step.step_id)
        create_placeholder_file(signoff, "SIMULATED SIGNOFF\n")


def _evaluate_acceptance(
    step: ProcessStep, config: RunConfig, placeholders: dict[str, str]
) -> tuple[bool, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    all_passed = True
    signoff = _signoff_path(_build_dir(config), step.step_id)

    for criterion in step.acceptance.criteria:
        if isinstance(criterion, str):
            text, optional = normalize_optional_name(criterion)
            if optional:
                results.append(
                    {
                        "criterion": text,
                        "status": "OPTIONAL",
                        "manual_signoff_required": False,
                    }
                )
                continue
            if signoff.exists():
                results.append(
                    {
                        "criterion": text,
                        "status": "PASS",
                        "manual_signoff_required": True,
                        "signoff_path": signoff.as_posix(),
                    }
                )
            else:
                results.append(
                    {
                        "criterion": text,
                        "status": "FAIL",
                        "manual_signoff_required": True,
                        "signoff_path": signoff.as_posix(),
                    }
                )
                all_passed = False
        elif isinstance(criterion, dict):
            criterion_type = str(criterion.get("type", "")).lower()
            path = criterion.get("path")
            if criterion_type == "file_exists" and isinstance(path, str):
                expanded = expand_placeholders(path, placeholders)
                try:
                    target = resolve_path(config.repo_root, expanded)
                    status = "PASS" if target.exists() else "FAIL"
                    if status == "FAIL":
                        all_passed = False
                    results.append(
                        {
                            "criterion": f"file_exists:{expanded}",
                            "status": status,
                            "manual_signoff_required": False,
                        }
                    )
                except ValueError as exc:
                    results.append(
                        {
                            "criterion": f"file_exists:{expanded}",
                            "status": "FAIL",
                            "manual_signoff_required": False,
                            "error": str(exc),
                        }
                    )
                    all_passed = False
            else:
                results.append(
                    {
                        "criterion": str(criterion),
                        "status": "FAIL",
                        "manual_signoff_required": False,
                    }
                )
                all_passed = False
        else:
            results.append(
                {
                    "criterion": str(criterion),
                    "status": "FAIL",
                    "manual_signoff_required": False,
                }
            )
            all_passed = False

    return all_passed, results


def _evaluate_evidence(
    step: ProcessStep, config: RunConfig, placeholders: dict[str, str]
) -> tuple[bool, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    all_present = True
    for evidence in step.evidence.required:
        name, optional = normalize_optional_name(evidence)
        if optional:
            results.append({"evidence": name, "status": "OPTIONAL"})
            continue
        expanded = expand_placeholders(name, placeholders)
        try:
            evidence_path = resolve_path(_build_dir(config), expanded)
            status = "PASS" if evidence_path.exists() else "FAIL"
            if status == "FAIL":
                all_present = False
            results.append({"evidence": expanded, "status": status})
        except ValueError as exc:
            results.append({"evidence": expanded, "status": "FAIL", "error": str(exc)})
            all_present = False
    return all_present, results


def _step_applicable(step: ProcessStep, block_level: BlockLevel) -> bool:
    if step.when is None:
        return True
    return _block_level_at_least(block_level, step.when.block_level_at_least)


def _write_hashes_file(build_dir: Path, hashes: dict[str, str]) -> None:
    lines = [f"{hashes[path]}  {path}" for path in sorted(hashes)]
    write_text(build_dir / "hashes.txt", "\n".join(lines) + "\n")


def _collect_files(build_dir: Path, exclude: set[str]) -> list[Path]:
    return [
        path
        for path in build_dir.rglob("*")
        if path.is_file() and path.relative_to(build_dir).as_posix() not in exclude
    ]


def run_traveler(
    spec_path: Path,
    build_id: str,
    rev_tag: str,
    block_level: BlockLevel,
    simulate: bool = False,
    lot_id: Optional[str] = None,
    ncr_id: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> Path:
    repo_root = repo_root or Path.cwd()
    env_lot_id = os.getenv("SFCS_LOT_ID")
    env_ncr_id = os.getenv("SFCS_NCR_ID")
    resolved_lot_id = lot_id if lot_id is not None else (env_lot_id or "LOT_SIM")
    resolved_ncr_id = ncr_id if ncr_id is not None else (env_ncr_id or "NCR_SIM")
    config = RunConfig(
        spec_path=spec_path,
        build_id=build_id,
        rev_tag=rev_tag,
        block_level=block_level,
        simulate=simulate,
        lot_id=resolved_lot_id,
        ncr_id=resolved_ncr_id,
        repo_root=repo_root,
    )

    spec_text = spec_path.read_text(encoding="utf-8")
    spec = load_spec(spec_path)
    validate_spec(spec)
    ordered_steps = topological_sort(spec.process_flow)

    build_dir = _build_dir(config)
    build_dir.mkdir(parents=True, exist_ok=True)
    runner_log = build_dir / "runner.log"
    if simulate:
        simulation_notice = build_dir / "SIMULATION_NOTICE.txt"
        create_placeholder_file(
            simulation_notice, "SIMULATED BUILD - NOT FOR PRODUCTION ACCEPTANCE\n"
        )

    run_id = _compute_run_id(config, spec_text)
    placeholders = _build_placeholders(config)
    manifest_output = expand_placeholders(spec.digital_thread.build_manifest.output, placeholders)
    manifest_path = resolve_path(config.repo_root, manifest_output)
    _create_manifest(config, manifest_path)
    traveler_path = build_dir / "traveler.yaml"
    _create_traveler(spec.model_dump(mode="json"), traveler_path)
    create_placeholder_file(build_dir / "hashes.txt")
    if simulate:
        ncr_path = resolve_path(
            config.repo_root, expand_placeholders("quality/ncr/<ncr_id>.yaml", placeholders)
        )
        write_yaml(
            ncr_path,
            {
                "ncr_id": config.ncr_id,
                "status": "SIMULATED",
                "disposition": "use_as_is",
            },
        )

    ledger: dict[str, Any] = {
        "run_id": run_id,
        "build_id": config.build_id,
        "rev_tag": config.rev_tag,
        "block_level": config.block_level.value,
        "simulate": simulate,
        "spec_path": spec_path.as_posix(),
        "spec_hash": sha256_bytes(spec_text.encode("utf-8")),
        "started_at": _utc_now(),
        "steps": [],
    }

    pipeline_failed = False
    gates_passed = True
    for step in ordered_steps:
        step_entry: dict[str, Any] = {
            "step_id": step.step_id,
            "name": step.name,
            "type": step.type.value,
            "prerequisites": step.prerequisites,
            "outputs": step.outputs,
            "inputs": step.inputs,
        }
        if pipeline_failed:
            step_entry["status"] = "SKIPPED"
            ledger["steps"].append(step_entry)
            continue
        if not _step_applicable(step, config.block_level):
            step_entry["status"] = "SKIPPED"
            ledger["steps"].append(step_entry)
            continue

        step_entry["started_at"] = _utc_now()
        _log_event(runner_log, {"event": "step_start", "step_id": step.step_id})

        if simulate:
            _create_simulated_outputs(step, config)

        evidence_ok, evidence_results = _evaluate_evidence(step, config, placeholders)
        acceptance_ok, acceptance_results = _evaluate_acceptance(step, config, placeholders)
        step_entry["evidence"] = evidence_results
        step_entry["acceptance"] = acceptance_results

        step_passed = evidence_ok and acceptance_ok
        step_entry["status"] = "PASS" if step_passed else "FAIL"
        step_entry["ended_at"] = _utc_now()
        ledger["steps"].append(step_entry)
        _log_event(
            runner_log,
            {"event": "step_end", "step_id": step.step_id, "status": step_entry["status"]},
        )

        if step.type == StepType.GATE and not step_passed:
            gates_passed = False
        if not step_passed:
            pipeline_failed = True

    ledger["ended_at"] = _utc_now()
    ledger["gates_passed"] = gates_passed
    ledger["final_disposition"] = "PASS" if not pipeline_failed and gates_passed else "FAIL"

    artifact_paths = _collect_files(build_dir, exclude={"ledger.json", "hashes.txt"})
    ledger["artifact_hashes"] = hash_files(artifact_paths, build_dir)
    write_json(build_dir / "ledger.json", ledger)

    hash_paths = _collect_files(build_dir, exclude={"hashes.txt"})
    _write_hashes_file(build_dir, hash_files(hash_paths, build_dir))
    return build_dir


def status_build(build_id: str, repo_root: Optional[Path] = None) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    ledger_path = repo_root / "records" / "builds" / build_id / "ledger.json"
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger not found for build_id {build_id}")
    return json.loads(ledger_path.read_text(encoding="utf-8"))


def package_build(build_id: str, repo_root: Optional[Path] = None) -> Path:
    repo_root = repo_root or Path.cwd()
    build_dir = repo_root / "records" / "builds" / build_id
    ledger = status_build(build_id, repo_root)
    if ledger.get("final_disposition") != "PASS":
        raise RuntimeError("Packaging blocked: final disposition is not PASS.")

    zip_path = build_dir / "acceptance_data_package.zip"
    file_paths = sorted(
        [path for path in build_dir.rglob("*") if path.is_file() and path != zip_path]
    )

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for path in file_paths:
            relative = path.relative_to(build_dir).as_posix()
            info = ZipInfo(relative)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            with path.open("rb") as handle:
                zip_file.writestr(info, handle.read())

    return zip_path
