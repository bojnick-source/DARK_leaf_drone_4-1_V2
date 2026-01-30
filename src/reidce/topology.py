from __future__ import annotations

from dataclasses import dataclass

from reidce.schemas import DesignSpec


@dataclass(frozen=True)
class TopologyCandidate:
    name: str
    design: DesignSpec
    rationale: str


def generate_topology_candidates(design: DesignSpec) -> list[TopologyCandidate]:
    candidates: list[TopologyCandidate] = []
    base_name = design.name
    for idx in range(1, 4):
        candidate = design.model_copy(
            update={"name": f"{base_name}_topology_{idx}"}
        )
        candidates.append(
            TopologyCandidate(
                name=candidate.name,
                design=candidate,
                rationale="Topology placeholder candidate.",
            )
        )
    return candidates
