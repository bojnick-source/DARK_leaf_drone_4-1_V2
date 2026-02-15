"""Latin Hypercube Sampling and advanced sampling strategies.

Latin Hypercube Sampling (LHS) partitions each input dimension into
*n* equal-probability strata and draws exactly one sample per stratum,
then randomly pairs strata across dimensions.  Compared with pure random
sampling, LHS guarantees better marginal coverage of the design space
with the same number of evaluations — a key advantage for
design-of-experiments and Monte Carlo integration where function
evaluations are expensive.

This module also provides quasi-random (Halton-style) sequences,
adaptive sampling that combines exploration with exploitation, and a
simple discrepancy metric for comparing sample quality.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SamplingBounds:
    """Axis-aligned hyper-rectangular bounds for sampling."""

    lower: list[float]
    upper: list[float]

    def __post_init__(self) -> None:
        if len(self.lower) != len(self.upper):
            raise ValueError("lower and upper must have the same length")
        for lo, hi in zip(self.lower, self.upper, strict=False):
            if lo >= hi:
                raise ValueError(
                    f"lower bound {lo} must be strictly less than upper {hi}"
                )

    @property
    def n_dims(self) -> int:
        """Number of dimensions."""
        return len(self.lower)


@dataclass
class SampleSet:
    """Container for a batch of multi-dimensional sample points."""

    samples: list[list[float]]
    method: str
    n_samples: int
    n_dims: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIRST_PRIMES: list[int] = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]


def _van_der_corput(index: int, base: int) -> float:
    """Return the *index*-th element of the Van der Corput sequence."""
    result = 0.0
    denom = 1.0
    n = index
    while n > 0:
        denom *= base
        n, remainder = divmod(n, base)
        result += remainder / denom
    return result


def _scale(value: float, lo: float, hi: float) -> float:
    """Scale a [0, 1] value to [lo, hi]."""
    return lo + value * (hi - lo)


# ---------------------------------------------------------------------------
# Sampling functions
# ---------------------------------------------------------------------------

def latin_hypercube_sample(
    bounds: SamplingBounds,
    n_samples: int,
    seed: int = 42,
) -> SampleSet:
    """Standard Latin Hypercube Sampling.

    Each dimension is divided into *n_samples* equal strata.  One point
    is drawn uniformly within each stratum, and the strata are randomly
    paired across dimensions via independent column permutations.
    """
    rng = random.Random(seed)
    n_dims = bounds.n_dims
    samples: list[list[float]] = [[] for _ in range(n_samples)]

    for d in range(n_dims):
        perm = list(range(n_samples))
        rng.shuffle(perm)
        lo, hi = bounds.lower[d], bounds.upper[d]
        stratum_size = (hi - lo) / n_samples
        for i in range(n_samples):
            stratum_lo = lo + perm[i] * stratum_size
            value = rng.uniform(stratum_lo, stratum_lo + stratum_size)
            samples[i].append(value)

    return SampleSet(
        samples=samples,
        method="lhs",
        n_samples=n_samples,
        n_dims=n_dims,
    )


def random_sample(
    bounds: SamplingBounds,
    n_samples: int,
    seed: int = 42,
) -> SampleSet:
    """Pure random uniform sampling."""
    rng = random.Random(seed)
    n_dims = bounds.n_dims
    samples: list[list[float]] = []
    for _ in range(n_samples):
        point = [
            rng.uniform(bounds.lower[d], bounds.upper[d])
            for d in range(n_dims)
        ]
        samples.append(point)

    return SampleSet(
        samples=samples,
        method="random",
        n_samples=n_samples,
        n_dims=n_dims,
    )


def sobol_like_sample(
    bounds: SamplingBounds,
    n_samples: int,
    seed: int = 42,
) -> SampleSet:
    """Quasi-random low-discrepancy sampling (Halton sequence).

    Uses Van der Corput sequences with prime bases (2, 3, 5, …) — one
    base per dimension.  A random offset drawn from *seed* is added
    (mod 1) to break alignment artefacts.
    """
    rng = random.Random(seed)
    n_dims = bounds.n_dims
    if n_dims > len(_FIRST_PRIMES):
        raise ValueError(
            f"sobol_like_sample supports up to {len(_FIRST_PRIMES)} "
            f"dimensions, got {n_dims}"
        )

    offsets = [rng.random() for _ in range(n_dims)]
    samples: list[list[float]] = []
    for i in range(1, n_samples + 1):
        point: list[float] = []
        for d in range(n_dims):
            raw = (_van_der_corput(i, _FIRST_PRIMES[d]) + offsets[d]) % 1.0
            point.append(_scale(raw, bounds.lower[d], bounds.upper[d]))
        samples.append(point)

    return SampleSet(
        samples=samples,
        method="sobol_like",
        n_samples=n_samples,
        n_dims=n_dims,
    )


def compute_discrepancy(
    sample_set: SampleSet,
    bounds: SamplingBounds,
) -> float:
    """Pairwise-distance coverage metric in [0, 1] (lower is better).

    Computes the average nearest-neighbour distance between sample
    points normalised by the diagonal of the bounding box.  A value
    close to 0 indicates dense, uniform coverage.
    """
    pts = sample_set.samples
    n = len(pts)
    if n <= 1:
        return 1.0

    diag = math.sqrt(
        sum(
            (hi - lo) ** 2
            for lo, hi in zip(bounds.lower, bounds.upper, strict=False)
        )
    )
    if diag == 0.0:
        return 1.0

    total_min_dist = 0.0
    for i in range(n):
        min_dist = float("inf")
        for j in range(n):
            if i == j:
                continue
            dist = math.sqrt(
                sum(
                    (pts[i][k] - pts[j][k]) ** 2
                    for k in range(sample_set.n_dims)
                )
            )
            if dist < min_dist:
                min_dist = dist
        total_min_dist += min_dist

    avg_nn = total_min_dist / n
    ideal_spacing = diag / (n ** (1.0 / max(sample_set.n_dims, 1)))
    if ideal_spacing == 0.0:
        return 1.0
    ratio = avg_nn / ideal_spacing
    return max(0.0, min(1.0, 1.0 - ratio))


def adaptive_sample(
    bounds: SamplingBounds,
    n_initial: int,
    n_refinement: int,
    score_fn: Any,
    seed: int = 42,
) -> SampleSet:
    """Adaptive sampling: LHS exploration then local refinement.

    1. Generate *n_initial* points via LHS.
    2. Evaluate *score_fn(point)* on each (higher score is better).
    3. Select the top 25 % of points as "elite" centers.
    4. Generate *n_refinement* new points by perturbing elite centers
       within a shrinking neighborhood (10 % of the range per dim).
    """
    initial = latin_hypercube_sample(bounds, n_initial, seed=seed)
    scored: list[tuple[float, list[float]]] = []
    for pt in initial.samples:
        scored.append((float(score_fn(pt)), pt))
    scored.sort(key=lambda t: t[0], reverse=True)

    elite_count = max(1, len(scored) // 4)
    elite = [pt for _, pt in scored[:elite_count]]

    rng = random.Random(seed + 1)
    refinement: list[list[float]] = []
    for idx in range(n_refinement):
        center = elite[idx % len(elite)]
        point: list[float] = []
        for d in range(bounds.n_dims):
            span = (bounds.upper[d] - bounds.lower[d]) * 0.1
            val = rng.gauss(center[d], span)
            val = max(bounds.lower[d], min(bounds.upper[d], val))
            point.append(val)
        refinement.append(point)

    all_samples = initial.samples + refinement
    return SampleSet(
        samples=all_samples,
        method="adaptive",
        n_samples=len(all_samples),
        n_dims=bounds.n_dims,
    )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sample_to_dict(
    sample: list[float],
    names: list[str],
) -> dict[str, float]:
    """Convert a sample vector to a named dictionary."""
    if len(sample) != len(names):
        raise ValueError("sample and names must have the same length")
    return dict(zip(names, sample, strict=False))
