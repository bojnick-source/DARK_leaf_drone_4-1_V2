from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from math import sqrt
from statistics import fmean
from typing import Sequence


def _numpy():
    if find_spec("numpy") is None:
        return None
    return import_module("numpy")


def centered_l2_discrepancy(samples: Sequence[Sequence[float]]) -> float:
    """Compute centered L2 discrepancy for samples in [0,1]^d."""
    np = _numpy()
    if np is not None:
        arr = np.array(samples, dtype=float)
        n, d = arr.shape
        term1 = (13.0 / 12.0) ** d
        term2 = (2.0 / n) * np.sum(
            np.prod(1 + 0.5 * np.abs(arr - 0.5) - 0.5 * (arr - 0.5) ** 2, axis=1)
        )
        diff = arr[:, None, :] - arr[None, :, :]
        term3 = (1.0 / (n**2)) * np.sum(
            np.prod(1 + 0.5 * np.abs(diff) - 0.5 * (diff**2), axis=2)
        )
        value = term1 - term2 + term3
        return float(np.sqrt(max(value, 0.0)))

    n = len(samples)
    if n == 0:
        return 0.0
    d = len(samples[0])
    term1 = (13.0 / 12.0) ** d
    term2_sum = 0.0
    for row in samples:
        prod = 1.0
        for value in row:
            diff = value - 0.5
            prod *= 1 + 0.5 * abs(diff) - 0.5 * diff * diff
        term2_sum += prod
    term2 = (2.0 / n) * term2_sum
    term3_sum = 0.0
    for i in range(n):
        for j in range(n):
            prod = 1.0
            for k in range(d):
                diff = samples[i][k] - samples[j][k]
                prod *= 1 + 0.5 * abs(diff) - 0.5 * diff * diff
            term3_sum += prod
    term3 = (1.0 / (n**2)) * term3_sum
    value = term1 - term2 + term3
    return sqrt(max(value, 0.0))


def min_pairwise_distance(samples: Sequence[Sequence[float]]) -> float:
    np = _numpy()
    if np is not None:
        arr = np.array(samples, dtype=float)
        if len(arr) < 2:
            return 0.0
        diff = arr[:, None, :] - arr[None, :, :]
        dist = np.sqrt(np.sum(diff**2, axis=2))
        dist[dist == 0] = np.inf
        return float(np.min(dist))

    n = len(samples)
    if n < 2:
        return 0.0
    min_dist = float("inf")
    for i in range(n):
        for j in range(i + 1, n):
            dist_sq = 0.0
            for k in range(len(samples[i])):
                diff = samples[i][k] - samples[j][k]
                dist_sq += diff * diff
            min_dist = min(min_dist, sqrt(dist_sq))
    return min_dist if min_dist != float("inf") else 0.0


def max_abs_correlation(samples: Sequence[Sequence[float]]) -> float:
    np = _numpy()
    if np is not None:
        arr = np.array(samples, dtype=float)
        if arr.shape[1] < 2:
            return 0.0
        corr = np.corrcoef(arr, rowvar=False)
        mask = ~np.eye(corr.shape[0], dtype=bool)
        return float(np.max(np.abs(corr[mask])))

    if not samples:
        return 0.0
    n = len(samples)
    d = len(samples[0])
    if d < 2:
        return 0.0
    columns = [[row[i] for row in samples] for i in range(d)]
    means = [fmean(col) for col in columns]
    variances = []
    for idx, col in enumerate(columns):
        mean = means[idx]
        variances.append(fmean([(value - mean) ** 2 for value in col]))
    max_corr = 0.0
    for i in range(d):
        for j in range(i + 1, d):
            if variances[i] == 0 or variances[j] == 0:
                corr = 0.0
            else:
                cov = fmean(
                    [
                        (columns[i][k] - means[i]) * (columns[j][k] - means[j])
                        for k in range(n)
                    ]
                )
                corr = cov / sqrt(variances[i] * variances[j])
            max_corr = max(max_corr, abs(corr))
    return max_corr
