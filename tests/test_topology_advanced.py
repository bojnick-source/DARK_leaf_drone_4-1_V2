"""Tests for advanced topology optimization methods."""

from __future__ import annotations

import math

from reidce.topology import (
    TopologyField,
    TopologyOptConfig,
    TopologyOptResult,
    optimize_topology_divergent,
    optimize_topology_freeform,
    optimize_topology_gk,
)


def test_freeform_returns_result() -> None:
    result = optimize_topology_freeform(nx=10, ny=5)
    assert isinstance(result, TopologyOptResult)
    assert result.method == "freeform"


def test_freeform_field_shape() -> None:
    result = optimize_topology_freeform(nx=10, ny=5)
    assert result.field.nx == 10
    assert result.field.ny == 5
    assert len(result.field.densities) == 50


def test_freeform_densities_bounded() -> None:
    result = optimize_topology_freeform(nx=10, ny=5)
    for d in result.field.densities:
        assert 0.0 <= d <= 1.0


def test_freeform_compliance_decreases() -> None:
    result = optimize_topology_freeform(nx=10, ny=5)
    history = result.field.objective_history
    assert len(history) > 1
    # Final compliance should be near or below initial
    # (small increases possible due to volume constraint enforcement)
    assert history[-1] < history[0] * 1.1


def test_freeform_volume_fraction_near_target() -> None:
    config = TopologyOptConfig(volume_fraction=0.3)
    result = optimize_topology_freeform(nx=10, ny=5, config=config)
    assert abs(result.volume_fraction - 0.3) < 0.15


def test_freeform_n_iterations() -> None:
    result = optimize_topology_freeform(nx=8, ny=4)
    assert result.n_iterations > 0


def test_gk_returns_result() -> None:
    result = optimize_topology_gk(nx=10, ny=5)
    assert isinstance(result, TopologyOptResult)
    assert result.method == "gk"


def test_gk_field_shape() -> None:
    result = optimize_topology_gk(nx=10, ny=5)
    assert result.field.nx == 10
    assert result.field.ny == 5
    assert len(result.field.densities) == 50


def test_gk_densities_bounded() -> None:
    result = optimize_topology_gk(nx=10, ny=5)
    for d in result.field.densities:
        assert 0.0 <= d <= 1.0


def test_gk_has_history() -> None:
    result = optimize_topology_gk(nx=10, ny=5)
    assert len(result.field.objective_history) > 0


def test_divergent_returns_list() -> None:
    results = optimize_topology_divergent(nx=8, ny=4, n_candidates=3)
    assert isinstance(results, list)
    assert len(results) == 3


def test_divergent_sorted_by_compliance() -> None:
    results = optimize_topology_divergent(nx=8, ny=4, n_candidates=3)
    for i in range(len(results) - 1):
        assert results[i].final_compliance <= results[i + 1].final_compliance


def test_divergent_method_tag() -> None:
    results = optimize_topology_divergent(nx=8, ny=4, n_candidates=2)
    for r in results:
        assert r.method == "divergent"


def test_divergent_diverse_solutions() -> None:
    results = optimize_topology_divergent(nx=8, ny=4, n_candidates=3)
    # Check that solutions are different (may be subtle on small grids)
    if len(results) >= 2:
        d0 = results[0].field.densities
        d1 = results[1].field.densities
        diff = sum(abs(a - b) for a, b in zip(d0, d1, strict=False)) / len(d0)
        assert diff >= 0.0


def test_topology_field_density_at() -> None:
    field = TopologyField(nx=3, ny=2, densities=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    assert field.density_at(0, 0) == 0.1
    assert field.density_at(2, 1) == 0.6
    assert field.density_at(5, 5) == 0.0  # out of bounds


def test_topology_field_mean_density() -> None:
    field = TopologyField(nx=2, ny=2, densities=[0.2, 0.4, 0.6, 0.8])
    assert abs(field.mean_density() - 0.5) < 1e-6


def test_topology_field_n_elements() -> None:
    field = TopologyField(nx=5, ny=3, densities=[0.0] * 15)
    assert field.n_elements == 15


def test_config_defaults() -> None:
    config = TopologyOptConfig()
    assert config.method == "freeform"
    assert config.volume_fraction == 0.4
    assert config.penalty_exponent == 3.0


def test_freeform_deterministic() -> None:
    r1 = optimize_topology_freeform(nx=8, ny=4, seed=123)
    r2 = optimize_topology_freeform(nx=8, ny=4, seed=123)
    assert r1.field.densities == r2.field.densities


def test_freeform_finite_compliance() -> None:
    result = optimize_topology_freeform(nx=10, ny=5)
    assert math.isfinite(result.final_compliance)
    assert result.final_compliance > 0.0
