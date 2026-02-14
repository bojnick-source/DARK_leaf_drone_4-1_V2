from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from reidce.memory import MemoryStore
from reidce.schemas import DesignSpec


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
        "deflection_capacity": 0.5 * stiffness * max_deflection * max_deflection,
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


# ── Advanced topology optimization methods ───────────────────────────────


@dataclass(frozen=True)
class TopologyOptConfig:
    """Configuration for advanced topology optimization."""

    method: str = "freeform"  # "freeform", "gk", "divergent"
    volume_fraction: float = 0.4
    penalty_exponent: float = 3.0
    filter_radius: float = 1.5
    n_iterations: int = 50
    convergence_tol: float = 1e-4
    min_density: float = 0.001


@dataclass
class TopologyField:
    """Density field representing material distribution."""

    nx: int
    ny: int
    densities: List[float]
    objective_history: List[float] = field(default_factory=list)
    method: str = "freeform"

    @property
    def n_elements(self) -> int:
        return self.nx * self.ny

    def density_at(self, ix: int, iy: int) -> float:
        if 0 <= ix < self.nx and 0 <= iy < self.ny:
            return self.densities[iy * self.nx + ix]
        return 0.0

    def mean_density(self) -> float:
        if not self.densities:
            return 0.0
        return sum(self.densities) / len(self.densities)

    def compliance(self) -> float:
        """Approximate structural compliance (lower is stiffer)."""
        if not self.objective_history:
            return float("inf")
        return self.objective_history[-1]


@dataclass(frozen=True)
class TopologyOptResult:
    """Result of an advanced topology optimization run."""

    field: TopologyField
    final_compliance: float
    volume_fraction: float
    n_iterations: int
    converged: bool
    method: str


def _element_stiffness(density: float, penalty: float) -> float:
    """SIMP (Solid Isotropic Material with Penalisation) stiffness."""
    return max(density, 1e-9) ** penalty


def _filter_densities(
    densities: List[float],
    nx: int,
    ny: int,
    radius: float,
) -> List[float]:
    """Density filter to avoid checkerboard patterns."""
    filtered = list(densities)
    r_int = max(1, int(radius))
    for iy in range(ny):
        for ix in range(nx):
            idx = iy * nx + ix
            total_weight = 0.0
            weighted_sum = 0.0
            for dy in range(-r_int, r_int + 1):
                for dx in range(-r_int, r_int + 1):
                    jx, jy = ix + dx, iy + dy
                    if 0 <= jx < nx and 0 <= jy < ny:
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist <= radius:
                            w = max(radius - dist, 0.0)
                            total_weight += w
                            weighted_sum += w * densities[jy * nx + jx]
            if total_weight > 0.0:
                filtered[idx] = weighted_sum / total_weight
    return filtered


def optimize_topology_freeform(
    nx: int = 20,
    ny: int = 10,
    config: TopologyOptConfig | None = None,
    seed: int = 42,
) -> TopologyOptResult:
    """Freeform topology optimization using SIMP method.

    Iteratively optimizes material distribution on a 2-D grid to
    minimize compliance (maximize stiffness) subject to a volume
    constraint.  Uses the Optimality Criteria (OC) update scheme.
    """
    import random as _random

    config = config or TopologyOptConfig(method="freeform")
    n = nx * ny
    _rng = _random.Random(seed)

    # Initialise uniform density field at volume fraction
    densities = [config.volume_fraction] * n
    history: List[float] = []

    for iteration in range(config.n_iterations):
        # Filter
        filtered = _filter_densities(densities, nx, ny, config.filter_radius)

        # Evaluate element compliance sensitivities (synthetic load case)
        compliance = 0.0
        sensitivities: List[float] = []
        for i in range(n):
            ke = _element_stiffness(filtered[i], config.penalty_exponent)
            # Synthetic unit-load compliance contribution
            load_factor = 1.0 + 0.3 * math.sin(
                math.pi * (i % nx) / max(nx - 1, 1)
            )
            ce = load_factor / max(ke, 1e-12)
            compliance += filtered[i] * ce
            dc = -config.penalty_exponent * (
                filtered[i] ** (config.penalty_exponent - 1.0)
            ) * ce
            sensitivities.append(dc)

        history.append(compliance)

        # Convergence check
        if (
            iteration > 0
            and abs(history[-1] - history[-2]) < config.convergence_tol
        ):
            break

        # OC update
        lam_lo, lam_hi = 1e-9, 1e9
        move = 0.2
        for _ in range(100):
            lam_mid = 0.5 * (lam_lo + lam_hi)
            new_densities: List[float] = []
            for i in range(n):
                be = max(
                    -sensitivities[i] / max(lam_mid, 1e-12), 1e-9
                )
                x_new = filtered[i] * math.sqrt(be)
                x_new = max(config.min_density, min(1.0, x_new))
                x_new = max(
                    filtered[i] - move, min(filtered[i] + move, x_new)
                )
                new_densities.append(x_new)
            vol = sum(new_densities) / n
            if vol > config.volume_fraction:
                lam_lo = lam_mid
            else:
                lam_hi = lam_mid
            if lam_hi - lam_lo < 1e-12:
                break
        densities = new_densities

    converged = (
        len(history) >= 2
        and abs(history[-1] - history[-2]) < config.convergence_tol
    )

    result_field = TopologyField(
        nx=nx,
        ny=ny,
        densities=densities,
        objective_history=history,
        method="freeform",
    )
    return TopologyOptResult(
        field=result_field,
        final_compliance=history[-1] if history else float("inf"),
        volume_fraction=sum(densities) / max(n, 1),
        n_iterations=len(history),
        converged=converged,
        method="freeform",
    )


def optimize_topology_gk(
    nx: int = 20,
    ny: int = 10,
    config: TopologyOptConfig | None = None,
    seed: int = 42,
) -> TopologyOptResult:
    """Ground-structure / GK topology optimization.

    Uses a growth-kernel approach: start from a sparse seed topology
    and iteratively grow material where stress is highest, prune where
    it is lowest.  Produces organic, branching structures.
    """
    config = config or TopologyOptConfig(method="gk")
    n = nx * ny

    densities = [config.min_density] * n
    # Seed: place material at load and support points
    for ix in range(nx):
        densities[0 * nx + ix] = 1.0  # bottom row (support)
    for iy in range(ny):
        densities[iy * nx + nx // 2] = 0.8  # centre column (load path)

    history: List[float] = []
    growth_rate = 0.15
    decay_rate = 0.05

    for iteration in range(config.n_iterations):
        filtered = _filter_densities(
            densities, nx, ny, config.filter_radius
        )

        compliance = 0.0
        stress: List[float] = []
        for i in range(n):
            ke = _element_stiffness(
                filtered[i], config.penalty_exponent
            )
            load_factor = 1.0 + 0.5 * math.cos(
                math.pi * (i // nx) / max(ny - 1, 1)
            )
            ce = load_factor / max(ke, 1e-12)
            compliance += filtered[i] * ce
            stress.append(ce * filtered[i])
        history.append(compliance)

        if (
            iteration > 0
            and abs(history[-1] - history[-2]) < config.convergence_tol
        ):
            break

        max_stress = max(stress) if stress else 1.0
        for i in range(n):
            normalised = stress[i] / max(max_stress, 1e-12)
            if normalised > 0.5:
                densities[i] = min(
                    1.0, filtered[i] + growth_rate * normalised
                )
            else:
                densities[i] = max(
                    config.min_density,
                    filtered[i] - decay_rate * (1.0 - normalised),
                )

        # Volume enforcement via proportional scaling
        vol = sum(densities) / n
        if vol > config.volume_fraction * 1.1:
            scale = config.volume_fraction / max(vol, 1e-12)
            densities = [
                max(config.min_density, d * scale) for d in densities
            ]

    converged = (
        len(history) >= 2
        and abs(history[-1] - history[-2]) < config.convergence_tol
    )

    result_field = TopologyField(
        nx=nx,
        ny=ny,
        densities=densities,
        objective_history=history,
        method="gk",
    )
    return TopologyOptResult(
        field=result_field,
        final_compliance=history[-1] if history else float("inf"),
        volume_fraction=sum(densities) / max(n, 1),
        n_iterations=len(history),
        converged=converged,
        method="gk",
    )


def optimize_topology_divergent(
    nx: int = 20,
    ny: int = 10,
    config: TopologyOptConfig | None = None,
    n_candidates: int = 5,
    seed: int = 42,
) -> List[TopologyOptResult]:
    """Divergent topology optimization — multiple distinct solutions.

    Generates *n_candidates* structurally diverse topologies by using
    different initialisation seeds and penalising similarity to
    previously found solutions.  Returns a list of results ranked by
    compliance (best first).
    """
    import random as _random

    config = config or TopologyOptConfig(method="divergent")
    results: List[TopologyOptResult] = []
    previous_densities: List[List[float]] = []
    n = nx * ny

    for c in range(n_candidates):
        c_seed = seed + c * 137
        c_rng = _random.Random(c_seed)

        vf = config.volume_fraction
        densities = [
            max(config.min_density, min(1.0, vf + c_rng.gauss(0.0, 0.15)))
            for _ in range(n)
        ]
        history: List[float] = []

        for iteration in range(config.n_iterations):
            filtered = _filter_densities(
                densities, nx, ny, config.filter_radius
            )

            compliance = 0.0
            sensitivities: List[float] = []
            for i in range(n):
                ke = _element_stiffness(
                    filtered[i], config.penalty_exponent
                )
                load_factor = 1.0 + 0.3 * math.sin(
                    math.pi * (i % nx) / max(nx - 1, 1)
                )
                ce = load_factor / max(ke, 1e-12)
                compliance += filtered[i] * ce

                dc = -config.penalty_exponent * (
                    filtered[i] ** (config.penalty_exponent - 1.0)
                ) * ce
                # Diversity penalty
                for prev in previous_densities:
                    sim = abs(filtered[i] - prev[i])
                    dc += 0.05 * (1.0 - sim)
                sensitivities.append(dc)

            history.append(compliance)

            if (
                iteration > 0
                and abs(history[-1] - history[-2])
                < config.convergence_tol
            ):
                break

            # OC update (same as freeform)
            lam_lo, lam_hi = 1e-9, 1e9
            move = 0.2
            for _ in range(80):
                lam_mid = 0.5 * (lam_lo + lam_hi)
                new_d: List[float] = []
                for i in range(n):
                    be = max(
                        -sensitivities[i] / max(lam_mid, 1e-12),
                        1e-9,
                    )
                    x_new = filtered[i] * math.sqrt(be)
                    x_new = max(config.min_density, min(1.0, x_new))
                    x_new = max(
                        filtered[i] - move,
                        min(filtered[i] + move, x_new),
                    )
                    new_d.append(x_new)
                vol = sum(new_d) / n
                if vol > config.volume_fraction:
                    lam_lo = lam_mid
                else:
                    lam_hi = lam_mid
                if lam_hi - lam_lo < 1e-12:
                    break
            densities = new_d

        converged = (
            len(history) >= 2
            and abs(history[-1] - history[-2]) < config.convergence_tol
        )
        result_field = TopologyField(
            nx=nx,
            ny=ny,
            densities=densities,
            objective_history=history,
            method="divergent",
        )
        results.append(
            TopologyOptResult(
                field=result_field,
                final_compliance=(
                    history[-1] if history else float("inf")
                ),
                volume_fraction=sum(densities) / max(n, 1),
                n_iterations=len(history),
                converged=converged,
                method="divergent",
            )
        )
        previous_densities.append(list(densities))

    results.sort(key=lambda r: r.final_compliance)
    return results
