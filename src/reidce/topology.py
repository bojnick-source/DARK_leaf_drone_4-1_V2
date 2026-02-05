from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from reidce.schemas import DesignSpec
from reidce.memory import MemoryStore


@dataclass(frozen=True)
class TopologyCandidate:
    name: str
    design: DesignSpec
    rationale: str
    score: float
    metrics: Dict[str, float]


@dataclass(frozen=True)
class TopologyPreference:
    stiffness_weight: float = 0.35
    pressure_weight: float = 0.25
    slenderness_weight: float = 0.2
    deflection_weight: float = 0.1
    diameter_penalty_weight: float = 0.1


@dataclass(frozen=True)
class TopologyScorecard:
    candidate: TopologyCandidate
    normalized_metrics: Dict[str, float]
    score: float


@dataclass(frozen=True)
class TopologyRecommendation:
    best: TopologyCandidate
    scorecard: TopologyScorecard
    ranked: list[TopologyScorecard]


def _scaled_quantity(quantity, scale: float, min_value: float | None = None):
    if quantity is None:
        return quantity
    value = quantity.value if quantity.value is not None else None
    if value is None:
        return quantity
    updated = value * scale
    if min_value is not None:
        updated = max(updated, min_value)
    return quantity.model_copy(update={"value": updated})


def _collect_metrics(candidate_design: DesignSpec) -> Dict[str, float]:
    geometry = candidate_design.geometry
    actuator = candidate_design.actuator
    structure = candidate_design.structure
    diameter = float(geometry.key_dimensions.actuator_diameter.value or 0.0)
    length = float(geometry.key_dimensions.actuator_length.value or 0.0)
    stiffness = float(structure.stiffness.value or 0.0)
    max_deflection = float(structure.max_deflection.value or 0.0)
    pressure = float(actuator.pressure_limit.value or 0.0)
    force_coeff = float(actuator.force_coeff.value or 0.0)
    span = max(diameter, 1e-6)
    return {
        "actuator_diameter_m": diameter,
        "actuator_length_m": length,
        "stiffness_n_per_m": stiffness,
        "pressure_force": pressure * force_coeff,
        "max_deflection_m": max_deflection,
        "deflection_capacity": stiffness * max_deflection,
        "slenderness": length / span,
    }


def _normalize(values: Iterable[float]) -> list[float]:
    values = list(values)
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        return [0.5 for _ in values]
    return [(value - vmin) / (vmax - vmin) for value in values]


def _build_candidate(design: DesignSpec, name: str, tag: str) -> TopologyCandidate:
    metrics = _collect_metrics(design)
    rationale = (
        f"{tag} candidate: stiffness={metrics['stiffness_n_per_m']:.1f} N/m, "
        f"pressure_force={metrics['pressure_force']:.1f}, slenderness={metrics['slenderness']:.2f}."
    )
    return TopologyCandidate(
        name=name,
        design=design,
        rationale=rationale,
        score=0.0,
        metrics=metrics,
    )


def _build_topology_variants(design: DesignSpec) -> list[TopologyCandidate]:
    candidates: list[TopologyCandidate] = []
    base_name = design.name
    base_geometry = design.geometry
    base_structure = design.structure
    base_actuator = design.actuator

    lightweight = design.model_copy(
        update={
            "name": f"{base_name}_topology_1",
            "geometry": base_geometry.model_copy(
                update={
                    "key_dimensions": base_geometry.key_dimensions.model_copy(
                        update={
                            "actuator_diameter": _scaled_quantity(
                                base_geometry.key_dimensions.actuator_diameter, 0.92, 0.001
                            ),
                            "actuator_wall_thickness": _scaled_quantity(
                                base_geometry.key_dimensions.actuator_wall_thickness, 0.9, 0.0002
                            ),
                            "actuator_length": _scaled_quantity(
                                base_geometry.key_dimensions.actuator_length, 0.95, 0.01
                            ),
                        }
                    )
                }
            ),
            "structure": base_structure.model_copy(
                update={
                    "stiffness": _scaled_quantity(base_structure.stiffness, 0.95, 1.0),
                    "max_deflection": _scaled_quantity(base_structure.max_deflection, 1.05, 0.0001),
                }
            ),
        }
    )
    candidates.append(_build_candidate(lightweight, lightweight.name, "Lightweight"))

    stiffened = design.model_copy(
        update={
            "name": f"{base_name}_topology_2",
            "geometry": base_geometry.model_copy(
                update={
                    "key_dimensions": base_geometry.key_dimensions.model_copy(
                        update={
                            "actuator_wall_thickness": _scaled_quantity(
                                base_geometry.key_dimensions.actuator_wall_thickness, 1.08, 0.0002
                            ),
                            "actuator_diameter": _scaled_quantity(
                                base_geometry.key_dimensions.actuator_diameter, 1.03, 0.001
                            ),
                        }
                    )
                }
            ),
            "structure": base_structure.model_copy(
                update={
                    "stiffness": _scaled_quantity(base_structure.stiffness, 1.1, 1.0),
                    "max_deflection": _scaled_quantity(base_structure.max_deflection, 0.9, 0.0001),
                }
            ),
        }
    )
    candidates.append(_build_candidate(stiffened, stiffened.name, "Stiffened"))

    reach = design.model_copy(
        update={
            "name": f"{base_name}_topology_3",
            "geometry": base_geometry.model_copy(
                update={
                    "key_dimensions": base_geometry.key_dimensions.model_copy(
                        update={
                            "actuator_length": _scaled_quantity(
                                base_geometry.key_dimensions.actuator_length, 1.12, 0.01
                            ),
                            "actuator_diameter": _scaled_quantity(
                                base_geometry.key_dimensions.actuator_diameter, 1.04, 0.001
                            ),
                        }
                    )
                }
            ),
            "structure": base_structure.model_copy(
                update={
                    "stiffness": _scaled_quantity(base_structure.stiffness, 1.04, 1.0),
                }
            ),
            "actuator": base_actuator.model_copy(
                update={
                    "force_coeff": _scaled_quantity(base_actuator.force_coeff, 1.03, 0.1),
                    "efficiency": _scaled_quantity(base_actuator.efficiency, 1.02, 0.1),
                }
            ),
        }
    )
    candidates.append(_build_candidate(reach, reach.name, "Reach"))

    return candidates


def rank_topology_candidates(
    design: DesignSpec,
    preference: TopologyPreference | None = None,
    memory_store: Optional[MemoryStore] = None,
) -> list[TopologyScorecard]:
    preference = preference or TopologyPreference()
    candidates = _build_topology_variants(design)
    metric_keys = [
        "stiffness_n_per_m",
        "pressure_force",
        "slenderness",
        "deflection_capacity",
        "actuator_diameter_m",
    ]
    metric_matrix = {key: _normalize([c.metrics[key] for c in candidates]) for key in metric_keys}
    ranked: list[TopologyScorecard] = []

    for idx, candidate in enumerate(candidates):
        normalized = {key: metric_matrix[key][idx] for key in metric_keys}
        score = (
            preference.stiffness_weight * normalized["stiffness_n_per_m"]
            + preference.pressure_weight * normalized["pressure_force"]
            + preference.slenderness_weight * normalized["slenderness"]
            + preference.deflection_weight * normalized["deflection_capacity"]
            - preference.diameter_penalty_weight * normalized["actuator_diameter_m"]
        )
        updated_candidate = candidate.design.model_copy(update={"name": candidate.name})
        ranked.append(
            TopologyScorecard(
                candidate=candidate.__class__(
                    name=candidate.name,
                    design=updated_candidate,
                    rationale=candidate.rationale,
                    score=score,
                    metrics=candidate.metrics,
                ),
                normalized_metrics=normalized,
                score=score,
            )
        )
    ranked = sorted(ranked, key=lambda item: item.score, reverse=True)
    if memory_store is not None:
        best = ranked[0]
        memory_store.log_event(
            "topology_rank",
            "Ranked topology candidates",
            {
                "best": best.candidate.name,
                "score": best.score,
                "design_id": design.design_id,
            },
        )
    return ranked


def recommend_topology(
    design: DesignSpec,
    preference: TopologyPreference | None = None,
    memory_store: Optional[MemoryStore] = None,
) -> TopologyRecommendation:
    ranked = rank_topology_candidates(design, preference, memory_store)
    best = ranked[0]
    return TopologyRecommendation(best=best.candidate, scorecard=best, ranked=ranked)


def generate_topology_candidates(design: DesignSpec) -> list[TopologyCandidate]:
    return [scorecard.candidate for scorecard in rank_topology_candidates(design)]
