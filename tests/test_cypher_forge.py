"""Tests for sfcs_mdp.cypher_forge — DARPA CyPhER Forge cipher loop."""

from sfcs_mdp.cypher_forge import (
    CYPHER_FORGE_PROGRAMME,
    CYPHER_FORGE_VERSION,
    CypherForgeSession,
    NextTestPoint,
    UncertaintyEstimate,
    assimilate_observation,
    check_safety,
    maximise_knowledge,
    quantify_uncertainty,
)

# ── Helpers ──────────────────────────────────────────────────────────────


def _simple_predict(inputs):
    """Deterministic surrogate: y1 = x0 + x1, y2 = x0 * x1."""
    return {"y1": inputs[0] + inputs[1], "y2": inputs[0] * inputs[1]}


# ── Uncertainty quantification ───────────────────────────────────────────


def test_quantify_uncertainty_returns_estimates() -> None:
    estimates = quantify_uncertainty(_simple_predict, [1.0, 2.0], n_samples=100)
    assert len(estimates) == 2
    names = {e.metric for e in estimates}
    assert "y1" in names
    assert "y2" in names


def test_quantify_uncertainty_has_spread() -> None:
    estimates = quantify_uncertainty(_simple_predict, [1.0, 2.0], n_samples=200)
    for est in estimates:
        assert est.p10 <= est.p50 <= est.p90
        assert est.spread >= 0.0
        assert est.samples == 200


def test_quantify_uncertainty_deterministic() -> None:
    a = quantify_uncertainty(_simple_predict, [1.0, 2.0], seed=7)
    b = quantify_uncertainty(_simple_predict, [1.0, 2.0], seed=7)
    for ea, eb in zip(a, b, strict=False):
        assert ea.p50 == eb.p50


# ── Data assimilation ────────────────────────────────────────────────────


def test_assimilate_moves_toward_observation() -> None:
    post, _, gain = assimilate_observation(
        prior_mean=10.0,
        prior_variance=1.0,
        observed=12.0,
        observation_variance=1.0,
    )
    assert 10.0 < post < 12.0
    assert 0.0 < gain < 1.0


def test_assimilate_trusts_observation_when_prior_uncertain() -> None:
    post, _, gain = assimilate_observation(
        prior_mean=10.0,
        prior_variance=100.0,
        observed=12.0,
        observation_variance=0.01,
    )
    assert abs(post - 12.0) < 0.5
    assert gain > 0.9


def test_assimilate_trusts_prior_when_observation_noisy() -> None:
    post, _, gain = assimilate_observation(
        prior_mean=10.0,
        prior_variance=0.01,
        observed=12.0,
        observation_variance=100.0,
    )
    assert abs(post - 10.0) < 0.5
    assert gain < 0.1


# ── Knowledge maximisation ───────────────────────────────────────────────


def test_maximise_knowledge_returns_proposal() -> None:
    ests = [
        UncertaintyEstimate(metric="y1", p10=2.8, p50=3.0, p90=3.2, samples=200),
        UncertaintyEstimate(metric="y2", p10=1.0, p50=2.0, p90=4.0, samples=200),
    ]
    proposal = maximise_knowledge(ests, [1.0, 2.0])
    assert isinstance(proposal, NextTestPoint)
    assert proposal.information_score > 0.0
    assert "y2" in proposal.rationale  # widest spread


def test_maximise_knowledge_empty_uncertainties() -> None:
    proposal = maximise_knowledge([], [1.0])
    assert proposal.information_score == 0.0


# ── Safety assurances ────────────────────────────────────────────────────


def test_check_safety_within_bounds() -> None:
    ests = [
        UncertaintyEstimate(metric="y1", p10=2.9, p50=3.0, p90=3.1, samples=200),
    ]
    results = check_safety(ests, {"y1": (0.0, 10.0)})
    assert len(results) == 1
    assert results[0].safe is True


def test_check_safety_violation() -> None:
    ests = [
        UncertaintyEstimate(metric="y1", p10=-1.0, p50=3.0, p90=3.1, samples=200),
    ]
    results = check_safety(ests, {"y1": (0.0, 10.0)})
    assert len(results) == 1
    assert results[0].safe is False


def test_check_safety_insufficient_samples() -> None:
    ests = [
        UncertaintyEstimate(metric="y1", p10=2.0, p50=3.0, p90=4.0, samples=10),
    ]
    results = check_safety(ests, {"y1": (0.0, 10.0)}, n_samples_required=100)
    assert len(results) == 1
    assert results[0].safe is False


# ── CypherForgeSession ──────────────────────────────────────────────────


def test_session_single_step() -> None:
    session = CypherForgeSession(predict_fn=_simple_predict, seed=42)
    step = session.run_step([1.0, 2.0])
    assert step.iteration == 0
    assert step.status in ("continue", "converged")
    assert len(step.uncertainties) == 2


def test_session_with_observations() -> None:
    session = CypherForgeSession(predict_fn=_simple_predict, seed=42)
    step = session.run_step([1.0, 2.0], observations={"y1": 3.5})
    assert len(step.assimilations) >= 1
    assim = step.assimilations[0]
    assert assim.metric == "y1"
    assert assim.observed == 3.5


def test_session_run_converges() -> None:
    session = CypherForgeSession(
        predict_fn=_simple_predict,
        convergence_threshold=10.0,  # easy convergence
        max_iterations=5,
        seed=42,
    )
    steps = session.run([1.0, 2.0])
    assert len(steps) >= 1
    assert steps[-1].status == "converged"


def test_session_run_respects_max_iterations() -> None:
    session = CypherForgeSession(
        predict_fn=_simple_predict,
        convergence_threshold=0.0,  # never converge
        max_iterations=3,
        seed=42,
    )
    steps = session.run([1.0, 2.0])
    assert len(steps) <= 3


def test_session_stops_on_unsafe() -> None:
    session = CypherForgeSession(
        predict_fn=_simple_predict,
        constraints={"y1": (100.0, 200.0)},  # impossible bounds
        max_iterations=5,
        seed=42,
    )
    steps = session.run([1.0, 2.0])
    assert steps[-1].status == "unsafe"


def test_session_summary() -> None:
    session = CypherForgeSession(
        predict_fn=_simple_predict,
        convergence_threshold=10.0,
        seed=42,
    )
    session.run([1.0, 2.0])
    summary = session.summary()
    assert summary["programme"] == CYPHER_FORGE_PROGRAMME
    assert summary["version"] == CYPHER_FORGE_VERSION
    assert summary["iterations"] >= 1
    assert len(summary["technologies"]) == 6


def test_session_history_immutable() -> None:
    session = CypherForgeSession(predict_fn=_simple_predict, seed=42)
    session.run_step([1.0, 2.0])
    h1 = session.history
    h1.clear()
    assert len(session.history) == 1  # original unmodified
