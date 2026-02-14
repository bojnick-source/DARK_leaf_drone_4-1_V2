"""Tests for reidce.cad_agent — competition drone CAD agent pipeline."""

from reidce.cad_agent import (
    CadAgentResult,
    CompetitionDroneSpec,
    generate_competition_drone_mesh,
    run_cad_agent,
)
from reidce.memory import MemoryStore

# ── CompetitionDroneSpec ─────────────────────────────────────────────


def test_default_spec_values() -> None:
    spec = CompetitionDroneSpec()
    assert spec.arm_count == 4
    assert spec.hub_radius_m > 0
    assert spec.motor_radius_m > 0
    assert spec.prop_radius_m > 0


def test_custom_spec() -> None:
    spec = CompetitionDroneSpec(arm_count=6, arm_length_m=0.4)
    assert spec.arm_count == 6
    assert spec.arm_length_m == 0.4


# ── generate_competition_drone_mesh ──────────────────────────────────


def test_generate_mesh_default() -> None:
    mesh = generate_competition_drone_mesh()
    assert mesh.statistics.vertex_count > 0
    assert mesh.statistics.triangle_count > 0
    assert mesh.statistics.edge_count > 0
    assert mesh.statistics.watertight is True


def test_generate_mesh_draft_quality() -> None:
    mesh = generate_competition_drone_mesh(quality="draft")
    assert mesh.statistics.quality_level == "draft"
    assert mesh.statistics.vertex_count > 0


def test_generate_mesh_high_fidelity() -> None:
    mesh = generate_competition_drone_mesh(quality="high_fidelity")
    assert mesh.statistics.quality_level == "high_fidelity"
    draft = generate_competition_drone_mesh(quality="draft")
    assert mesh.statistics.triangle_count > draft.statistics.triangle_count


def test_generate_mesh_custom_spec() -> None:
    spec = CompetitionDroneSpec(arm_count=6)
    mesh = generate_competition_drone_mesh(spec)
    assert mesh.statistics.vertex_count > 0
    # 6-arm drone should have more geometry than 4-arm
    mesh4 = generate_competition_drone_mesh(CompetitionDroneSpec(arm_count=4))
    assert mesh.statistics.triangle_count > mesh4.statistics.triangle_count


def test_mesh_has_positive_surface_area() -> None:
    mesh = generate_competition_drone_mesh()
    assert mesh.statistics.surface_area > 0.0


def test_mesh_bounding_box_valid() -> None:
    mesh = generate_competition_drone_mesh()
    bb_min = mesh.statistics.bounding_box_min
    bb_max = mesh.statistics.bounding_box_max
    assert bb_max.x > bb_min.x
    assert bb_max.y > bb_min.y
    assert bb_max.z > bb_min.z


def test_mesh_hash_deterministic() -> None:
    m1 = generate_competition_drone_mesh(quality="standard")
    m2 = generate_competition_drone_mesh(quality="standard")
    assert m1.geometry_hash == m2.geometry_hash


def test_mesh_hash_varies_with_quality() -> None:
    draft = generate_competition_drone_mesh(quality="draft")
    hf = generate_competition_drone_mesh(quality="high_fidelity")
    assert draft.geometry_hash != hf.geometry_hash


# ── run_cad_agent ────────────────────────────────────────────────────


def test_run_cad_agent_default() -> None:
    result = run_cad_agent()
    assert isinstance(result, CadAgentResult)
    assert result.competition_focused is True
    assert result.component_count > 0
    assert result.mesh.statistics.vertex_count > 0
    assert "watertight" in result.validation
    assert len(result.topology_scores) > 0


def test_run_cad_agent_high_fidelity() -> None:
    result = run_cad_agent(quality="high_fidelity")
    assert result.quality == "high_fidelity"
    assert result.mesh.statistics.triangle_count > 0


def test_run_cad_agent_custom_spec() -> None:
    spec = CompetitionDroneSpec(arm_count=6, arm_length_m=0.4)
    result = run_cad_agent(spec=spec)
    assert result.spec.arm_count == 6
    assert result.component_count == 1 + 6 * 3 + 1  # hub + 6*(arm+motor+prop) + battery


def test_run_cad_agent_validation_passes() -> None:
    result = run_cad_agent()
    assert result.validation["vertex_count"] > 0
    assert result.validation["face_count"] > 0
    assert result.validation["surface_area"] > 0.0


def test_run_cad_agent_topology_scores() -> None:
    result = run_cad_agent()
    metrics = {s["metric"] for s in result.topology_scores}
    assert "arm_slenderness" in metrics
    assert "prop_to_hub_ratio" in metrics
    assert "mass_efficiency_index" in metrics


def test_run_cad_agent_with_memory_store() -> None:
    mem = MemoryStore()
    result = run_cad_agent(memory_store=mem)
    assert result.competition_focused is True
    events = [r for r in mem.records if "cad_agent" in r.tags]
    assert len(events) >= 1
