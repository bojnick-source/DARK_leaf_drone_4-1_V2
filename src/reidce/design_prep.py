from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sfcs_mdp.hashutil import sha256_bytes

from reidce.memory import MemoryStore
from reidce.schemas import CadRef, DesignSpec, GeometrySpec
from reidce.topology import recommend_topology


@dataclass(frozen=True)
class PicoGKResult:
    cad_ref: CadRef
    geom_hash: str
    source: str


def _hash_geometry(geometry: GeometrySpec) -> str:
    payload = geometry.model_dump(mode="json", by_alias=True)
    return sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))


def generate_cad_ref(geometry: GeometrySpec, source: str = "pico_gk_stub") -> PicoGKResult:
    geom_hash = _hash_geometry(geometry)
    cad_ref = CadRef(type="implicit", uri=f"pico_gk://{geom_hash}", sha256=geom_hash)
    return PicoGKResult(cad_ref=cad_ref, geom_hash=geom_hash, source=source)


def apply_pico_gk(design: DesignSpec, source: str = "pico_gk_stub") -> DesignSpec:
    if design.geometry.cad_ref.type != "none":
        return design
    result = generate_cad_ref(design.geometry, source)
    updated_geometry = design.geometry.model_copy(update={"cad_ref": result.cad_ref})
    return design.model_copy(update={"geometry": updated_geometry})


def prepare_design_for_pipeline(design: Any, memory_store: MemoryStore | None = None) -> Any:
    """
    Prepare a design for pipeline processing.

    Applies PicoGK CAD reference generation and topology optimization
    if applicable to the design domain.

    Args:
        design: The design specification to prepare
        memory_store: Optional memory store for logging events

    Returns:
        Updated design specification with CAD reference and optimized topology
    """
    if not hasattr(design, "geometry") or not hasattr(design, "model_copy"):
        return design

    updated = apply_pico_gk(design)
    if memory_store is not None and updated is not design:
        cad_ref = getattr(updated.geometry, "cad_ref", None)
        cad_payload = cad_ref.model_dump(mode="json") if cad_ref is not None else None
        memory_store.log_event(
            "pico_gk",
            "Applied Pico GK CAD ref",
            {
                "design_id": getattr(updated, "design_id", None),
                "cad_ref": cad_payload,
            },
        )

    if getattr(updated, "domain", None) == "actuated_compliant_subsystem":
        recommendation = recommend_topology(updated, memory_store=memory_store)
        updated = recommendation.best.design
        if memory_store is not None:
            memory_store.log_event(
                "topology_recommendation",
                "Selected topology candidate",
                {
                    "design_id": getattr(updated, "design_id", None),
                    "candidate": recommendation.best.name,
                    "score": recommendation.scorecard.score,
                },
            )

    return updated
