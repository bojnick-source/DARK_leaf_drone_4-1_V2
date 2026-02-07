from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from statistics import fmean, pvariance
from typing import Any, Iterable

from topopt.uq.lhs import VariableSpec, _apply_distribution
from topopt.uq.metrics import max_abs_correlation, min_pairwise_distance

from .solver import evaluate_sample


def _evaluate_parallel(samples: list[dict[str, float]], benchmark_id: str, workers: int) -> list[float]:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(evaluate_sample, sample, benchmark_id) for sample in samples]
        results = []
        for future in futures:
            result = future.result()
            results.append(result.objective)
        return results


def _to_sample_dict(samples: dict[str, list[float]]) -> list[dict[str, float]]:
    keys = list(samples.keys())
    total = len(samples[keys[0]])
    rows = []
    for idx in range(total):
        row = {key: float(samples[key][idx]) for key in keys}
        rows.append(row)
    return rows


def _generate_secondary_samples(
    unit_samples: list[list[float]],
    variables: Iterable[VariableSpec],
) -> tuple[dict[str, list[float]], dict[str, Any]]:
    variables = list(variables)
    variance_reduction = {
        "technique": "N/A",
        "reason": "Discrete or mixed marginals prevent antithetic pairing.",
    }
    if all(spec.choices is None for spec in variables):
        antithetic_unit = [[1.0 - value for value in row] for row in unit_samples]
        secondary = {}
        for idx, spec in enumerate(variables):
            column = [row[idx] for row in antithetic_unit]
            secondary[spec.name] = _apply_distribution(column, spec)
        variance_reduction = {
            "technique": "antithetic",
            "reason": "Applied to continuous marginals.",
        }
        return secondary, variance_reduction
    secondary = {}
    for idx, spec in enumerate(variables):
        column = [row[idx] for row in unit_samples]
        secondary[spec.name] = _apply_distribution(column, spec)
    return secondary, variance_reduction


def robust_summary(
    samples: dict[str, list[float]],
    unit_samples: list[list[float]],
    variables: Iterable[VariableSpec],
    benchmark_id: str,
    parallel_workers: int,
) -> dict[str, Any]:
    sample_rows = _to_sample_dict(samples)
    objectives = _evaluate_parallel(sample_rows, benchmark_id, parallel_workers)
    mean_obj = float(fmean(objectives))
    var_obj = float(pvariance(objectives))
    primary_objective = mean_obj + 0.5 * (var_obj**0.5)

    secondary_samples, variance_reduction = _generate_secondary_samples(unit_samples, variables)
    secondary_rows = _to_sample_dict(secondary_samples)
    secondary_objectives = _evaluate_parallel(secondary_rows, benchmark_id, parallel_workers)

    secondary_mean = float(fmean(secondary_objectives))
    secondary_var = float(pvariance(secondary_objectives))

    return {
        "primary": {
            "mean": mean_obj,
            "variance": var_obj,
            "objective": primary_objective,
        },
        "secondary": {
            "mean": secondary_mean,
            "variance": secondary_var,
            "objective": secondary_mean + 0.5 * (secondary_var**0.5),
            "variance_reduction": variance_reduction,
        },
        "sample_stats": {
            "min_pairwise_distance": min_pairwise_distance(unit_samples),
            "max_abs_correlation": max_abs_correlation(unit_samples),
        },
        "per_sample": objectives,
    }
