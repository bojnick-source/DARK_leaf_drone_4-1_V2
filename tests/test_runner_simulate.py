import json
from pathlib import Path

from sfcs_mdp.model import BlockLevel
from sfcs_mdp.runner import package_build, run_traveler
from sfcs_mdp.validate import load_spec

SPEC_PATH = Path(__file__).resolve().parents[1] / "manufacturing" / "sfcs_drone_mdp_v0.yaml"


def test_simulated_run_end_to_end(tmp_path: Path) -> None:
    build_id = "BUILD_0001"
    build_dir = run_traveler(
        spec_path=SPEC_PATH,
        build_id=build_id,
        rev_tag="REV_A",
        block_level=BlockLevel.BLOCK_0_STRUCTURE_ONLY,
        simulate=True,
        repo_root=tmp_path,
    )

    ledger = json.loads((build_dir / "ledger.json").read_text(encoding="utf-8"))
    spec = load_spec(SPEC_PATH)

    assert ledger["final_disposition"] == "PASS"
    assert len(ledger["steps"]) == len(spec.process_flow)
    assert (build_dir / "hashes.txt").exists()
    assert not (build_dir / "acceptance_data_package.zip").exists()

    package_path = package_build(build_id, repo_root=tmp_path)
    assert package_path.exists()


def test_acceptance_requires_signoff(tmp_path: Path) -> None:
    build_id = "BUILD_SIGNOFF"
    build_dir = run_traveler(
        spec_path=SPEC_PATH,
        build_id=build_id,
        rev_tag="REV_A",
        block_level=BlockLevel.BLOCK_0_STRUCTURE_ONLY,
        simulate=False,
        repo_root=tmp_path,
    )
    ledger = json.loads((build_dir / "ledger.json").read_text(encoding="utf-8"))
    first_step = ledger["steps"][0]
    criterion = first_step["acceptance"][0]
    assert criterion["manual_signoff_required"] is True
    assert criterion["status"] == "FAIL"
