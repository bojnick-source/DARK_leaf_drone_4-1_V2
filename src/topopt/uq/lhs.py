from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt
import random
from statistics import NormalDist
from typing import Any, Iterable

from .metrics import centered_l2_discrepancy, max_abs_correlation, min_pairwise_distance


@dataclass
class VariableSpec:
    name: str
    dist: str
    params: dict[str, Any]
    choices: list[Any] | None = None


def _lhs_unit(n: int, dim: int, rng: random.Random) -> list[list[float]]:
    samples: list[list[float]] = []
    for _ in range(n):
        samples.append([0.0] * dim)
    for j in range(dim):
        points = [(i + rng.random()) / n for i in range(n)]
        rng.shuffle(points)
        for i in range(n):
            samples[i][j] = points[i]
    return samples


def _normal_ppf(u: float) -> float:
    dist = NormalDist()
    eps = 1e-12
    value = min(max(u, eps), 1 - eps)
    return dist.inv_cdf(value)


def _apply_distribution(u: list[float], spec: VariableSpec) -> list[float]:
    if spec.choices is not None:
        choices = spec.choices
        idxs = [min(int(value * len(choices)), len(choices) - 1) for value in u]
        return [choices[i] for i in idxs]

    dist = spec.dist
    params = spec.params
    if dist == "uniform":
        low, high = params["low"], params["high"]
        return [low + (high - low) * value for value in u]
    if dist == "normal":
        mean, std = params["mean"], params["std"]
        return [mean + std * _normal_ppf(value) for value in u]
    if dist == "lognormal":
        mean, sigma = params["mean"], params["sigma"]
        return [exp(mean + sigma * _normal_ppf(value)) for value in u]
    if dist == "triangular":
        left, mode, right = params["left"], params["mode"], params["right"]
        c = (mode - left) / (right - left)
        values = []
        for value in u:
            if value < c:
                values.append(left + sqrt(value * (right - left) * (mode - left)))
            else:
                values.append(right - sqrt((1 - value) * (right - left) * (right - mode)))
        return values
    raise ValueError(f"Unsupported distribution: {dist}")


def _score(samples: list[list[float]], corr_weight: float) -> float:
    min_dist = min_pairwise_distance(samples)
    corr = max_abs_correlation(samples)
    return min_dist - corr_weight * corr


def generate_lhs(
    n: int,
    variables: Iterable[VariableSpec],
    seed: int | None = None,
    maximin: bool = True,
    attempts: int = 20,
    corr_weight: float = 0.1,
) -> dict[str, Any]:
    variables = list(variables)
    rng = random.Random(seed)
    dim = len(variables)

    best_unit = None
    best_score = float("-inf")
    attempts = max(attempts, 1)

    for _ in range(attempts):
        unit = _lhs_unit(n, dim, rng)
        score = _score(unit, corr_weight) if maximin else 0.0
        if score > best_score or best_unit is None:
            best_unit = unit
            best_score = score

    if best_unit is None:
        best_unit = _lhs_unit(n, dim, rng)

    transformed = {}
    for idx, spec in enumerate(variables):
        column = [row[idx] for row in best_unit]
        transformed[spec.name] = _apply_distribution(column, spec)

    metrics = {
        "centered_l2_discrepancy": centered_l2_discrepancy(best_unit),
        "min_pairwise_distance": min_pairwise_distance(best_unit),
        "max_abs_correlation": max_abs_correlation(best_unit),
    }

    return {
        "unit_samples": best_unit,
        "samples": transformed,
        "metrics": metrics,
        "batching_mode": "BATCHED-NON-SLHS",
    }


def batch_samples(samples: dict[str, list[float]], batch_size: int) -> list[dict[str, list[float]]]:
    total = len(next(iter(samples.values())))
    batches = []
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = {key: value[start:end] for key, value in samples.items()}
        batches.append(batch)
    return batches
