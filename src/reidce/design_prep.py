from __future__ import annotations

from typing import Any

from reidce.memory import MemoryStore
from reidce.topology import recommend_topology


def prepare_design_for_pipeline(design: Any, memory_store: MemoryStore | None = None) -> Any:
    """
    Prepare a design for pipeline processing.

    Applies topology optimization if applicable to the design domain.

    Args:
        design: The design specification to prepare
        memory_store: Optional memory store for logging events

    Returns:
        Updated design specification with optimized topology
    """
    if not hasattr(design, "model_copy"):
        return design

    updated = design

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
