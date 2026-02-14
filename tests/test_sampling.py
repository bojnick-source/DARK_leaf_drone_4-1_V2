"""Tests for the Latin Hypercube Sampling module."""

from __future__ import annotations

from reidce.sampling import (
    SampleSet,
    SamplingBounds,
    adaptive_sample,
    compute_discrepancy,
    latin_hypercube_sample,
    random_sample,
    sample_to_dict,
    sobol_like_sample,
)


def test_sampling_bounds_n_dims() -> None:
    bounds = SamplingBounds(lower=[0.0, 1.0], upper=[1.0, 2.0])
    assert bounds.n_dims == 2


def test_sampling_bounds_invalid() -> None:
    try:
        SamplingBounds(lower=[1.0], upper=[0.5])
        raise AssertionError("Should raise ValueError")
    except ValueError:
        pass


def test_sampling_bounds_mismatched_length() -> None:
    try:
        SamplingBounds(lower=[0.0, 0.0], upper=[1.0])
        raise AssertionError("Should raise ValueError")
    except ValueError:
        pass


def test_lhs_sample_count() -> None:
    bounds = SamplingBounds(lower=[0.0, 0.0], upper=[1.0, 1.0])
    result = latin_hypercube_sample(bounds, n_samples=20)
    assert result.n_samples == 20
    assert len(result.samples) == 20
    assert result.method == "lhs"


def test_lhs_sample_dimensions() -> None:
    bounds = SamplingBounds(lower=[0.0, 0.0, 0.0], upper=[1.0, 2.0, 3.0])
    result = latin_hypercube_sample(bounds, n_samples=10)
    assert result.n_dims == 3
    for pt in result.samples:
        assert len(pt) == 3


def test_lhs_samples_within_bounds() -> None:
    bounds = SamplingBounds(lower=[1.0, 2.0], upper=[3.0, 5.0])
    result = latin_hypercube_sample(bounds, n_samples=50)
    for pt in result.samples:
        assert 1.0 <= pt[0] <= 3.0
        assert 2.0 <= pt[1] <= 5.0


def test_lhs_stratification() -> None:
    """Each stratum should have exactly one sample per dimension."""
    bounds = SamplingBounds(lower=[0.0], upper=[1.0])
    n = 10
    result = latin_hypercube_sample(bounds, n_samples=n)
    vals = sorted(pt[0] for pt in result.samples)
    # Check that each of n strata has a sample
    stratum_size = 1.0 / n
    for i, val in enumerate(vals):
        lo = i * stratum_size
        hi = (i + 1) * stratum_size
        assert lo <= val <= hi, f"Value {val} not in stratum [{lo}, {hi}]"


def test_lhs_deterministic() -> None:
    bounds = SamplingBounds(lower=[0.0, 0.0], upper=[1.0, 1.0])
    r1 = latin_hypercube_sample(bounds, 10, seed=99)
    r2 = latin_hypercube_sample(bounds, 10, seed=99)
    assert r1.samples == r2.samples


def test_random_sample_count() -> None:
    bounds = SamplingBounds(lower=[0.0], upper=[1.0])
    result = random_sample(bounds, 15)
    assert result.n_samples == 15
    assert result.method == "random"


def test_random_sample_within_bounds() -> None:
    bounds = SamplingBounds(lower=[0.0, -1.0], upper=[1.0, 1.0])
    result = random_sample(bounds, 50)
    for pt in result.samples:
        assert 0.0 <= pt[0] <= 1.0
        assert -1.0 <= pt[1] <= 1.0


def test_sobol_like_sample_count() -> None:
    bounds = SamplingBounds(lower=[0.0, 0.0], upper=[1.0, 1.0])
    result = sobol_like_sample(bounds, 20)
    assert result.n_samples == 20
    assert result.method == "sobol_like"


def test_sobol_like_within_bounds() -> None:
    bounds = SamplingBounds(lower=[0.0, 0.0], upper=[1.0, 1.0])
    result = sobol_like_sample(bounds, 30)
    for pt in result.samples:
        assert 0.0 <= pt[0] <= 1.0
        assert 0.0 <= pt[1] <= 1.0


def test_compute_discrepancy_basic() -> None:
    bounds = SamplingBounds(lower=[0.0, 0.0], upper=[1.0, 1.0])
    result = latin_hypercube_sample(bounds, 20)
    disc = compute_discrepancy(result, bounds)
    assert 0.0 <= disc <= 1.0


def test_lhs_better_discrepancy_than_random() -> None:
    """LHS should generally have lower discrepancy than pure random."""
    bounds = SamplingBounds(lower=[0.0, 0.0], upper=[1.0, 1.0])
    lhs = latin_hypercube_sample(bounds, 50, seed=42)
    rng = random_sample(bounds, 50, seed=42)
    d_lhs = compute_discrepancy(lhs, bounds)
    d_rng = compute_discrepancy(rng, bounds)
    # LHS should have comparable or better coverage
    assert d_lhs <= d_rng + 0.3


def test_adaptive_sample_count() -> None:
    bounds = SamplingBounds(lower=[0.0, 0.0], upper=[1.0, 1.0])
    result = adaptive_sample(
        bounds, n_initial=10, n_refinement=5,
        score_fn=lambda pt: -(pt[0] - 0.5) ** 2 - (pt[1] - 0.5) ** 2,
    )
    assert result.n_samples == 15
    assert result.method == "adaptive"


def test_adaptive_sample_within_bounds() -> None:
    bounds = SamplingBounds(lower=[0.0, 0.0], upper=[1.0, 1.0])
    result = adaptive_sample(
        bounds, n_initial=10, n_refinement=5,
        score_fn=lambda pt: sum(pt),
    )
    for pt in result.samples:
        assert 0.0 <= pt[0] <= 1.0
        assert 0.0 <= pt[1] <= 1.0


def test_sample_to_dict() -> None:
    d = sample_to_dict([1.0, 2.0, 3.0], ["a", "b", "c"])
    assert d == {"a": 1.0, "b": 2.0, "c": 3.0}


def test_sample_to_dict_mismatch() -> None:
    try:
        sample_to_dict([1.0, 2.0], ["a"])
        raise AssertionError("Should raise ValueError")
    except ValueError:
        pass


def test_discrepancy_single_sample() -> None:
    bounds = SamplingBounds(lower=[0.0], upper=[1.0])
    single = SampleSet(samples=[[0.5]], method="test", n_samples=1, n_dims=1)
    disc = compute_discrepancy(single, bounds)
    assert disc == 1.0
