from pathlib import Path

import pytest
import yaml

from sfcs_mdp.artifacts import expand_placeholders
from sfcs_mdp.model import Spec
from sfcs_mdp.validate import SpecValidationError, load_spec, validate_spec

SPEC_PATH = Path(__file__).resolve().parents[1] / "manufacturing" / "sfcs_drone_mdp_v0.yaml"


def test_load_spec_and_validate() -> None:
    spec = load_spec(SPEC_PATH)
    validate_spec(spec)
    assert len(spec.process_flow) > 0


def test_duplicate_step_ids_rejected() -> None:
    data = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    data["process_flow"].append(data["process_flow"][0])
    spec = Spec.model_validate(data)
    with pytest.raises(SpecValidationError):
        validate_spec(spec)


def test_missing_prerequisite_rejected() -> None:
    data = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    data["process_flow"][1]["prerequisites"] = ["MISSING"]
    spec = Spec.model_validate(data)
    with pytest.raises(SpecValidationError):
        validate_spec(spec)


def test_placeholder_expansion() -> None:
    expanded = expand_placeholders(
        "records/builds/<build_id>/cad_<REV_TAG>_<lot_id>.json",
        {"build_id": "B1", "REV_TAG": "REV_A", "lot_id": "LOT123", "ncr_id": "N1"},
    )
    assert expanded == "records/builds/B1/cad_REV_A_LOT123.json"
