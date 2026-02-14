"""Tests for reidce.unified_learning — unified linear learning runtime."""

from reidce.unified_learning import (
    DataSource,
    LearningRecord,
    LearningRuntime,
    LinearModel,
    OnlineModel,
    RuntimeMetrics,
)

# ── LinearModel ──────────────────────────────────────────────────────────


def test_linear_model_fit_and_predict() -> None:
    model = LinearModel()
    # Simple y = 2*x + 1
    x_data = [[1.0], [2.0], [3.0], [4.0]]
    y_data = [[3.0], [5.0], [7.0], [9.0]]
    model.fit(x_data, y_data)
    assert model.is_fitted()
    pred = model.predict([5.0])
    assert abs(pred[0] - 11.0) < 0.1


def test_linear_model_multi_output() -> None:
    model = LinearModel()
    x_data = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
    y_data = [[3.0, 1.0], [7.0, 2.0], [11.0, 3.0], [15.0, 4.0]]
    model.fit(x_data, y_data)
    pred = model.predict([9.0, 10.0])
    assert len(pred) == 2
    assert model.n_features == 2
    assert model.n_targets == 2


def test_linear_model_residual_mse() -> None:
    model = LinearModel()
    x_data = [[1.0], [2.0], [3.0]]
    y_data = [[2.0], [4.0], [6.0]]
    model.fit(x_data, y_data)
    mse = model.residual_mse(x_data, y_data)
    assert mse < 0.01


def test_linear_model_feature_importance() -> None:
    model = LinearModel()
    x_data = [[1.0, 0.0], [2.0, 0.0], [3.0, 0.0], [4.0, 0.0]]
    y_data = [[2.0], [4.0], [6.0], [8.0]]
    model.fit(x_data, y_data)
    assert len(model.feature_importance) == 2
    # First feature should be more important
    assert model.feature_importance[0] > model.feature_importance[1]


def test_linear_model_serialization() -> None:
    model = LinearModel()
    model.fit([[1.0], [2.0]], [[3.0], [5.0]])
    d = model.to_dict()
    assert d["schema"] == "dark/linear_model/1.0"
    restored = LinearModel.from_dict(d)
    assert restored.is_fitted()
    assert restored.n_features == 1


def test_linear_model_predict_batch() -> None:
    model = LinearModel()
    model.fit([[1.0], [2.0], [3.0]], [[2.0], [4.0], [6.0]])
    batch = model.predict_batch([[4.0], [5.0]])
    assert len(batch) == 2


# ── OnlineModel ──────────────────────────────────────────────────────────


def test_online_model_partial_fit() -> None:
    model = OnlineModel(learning_rate=0.01)
    loss1 = model.partial_fit([1.0, 2.0], [3.0])
    assert model.is_initialized()
    assert loss1 >= 0.0
    # Second step should exist
    loss2 = model.partial_fit([2.0, 3.0], [5.0])
    assert loss2 >= 0.0


def test_online_model_predict() -> None:
    model = OnlineModel(learning_rate=0.01)
    for _ in range(50):
        model.partial_fit([1.0], [2.0])
        model.partial_fit([2.0], [4.0])
    pred = model.predict([3.0])
    assert len(pred) == 1


def test_online_model_serialization() -> None:
    model = OnlineModel(learning_rate=0.005, degree=2)
    model.partial_fit([1.0, 2.0], [3.0])
    d = model.to_dict()
    assert d["schema"] == "dark/online_model/1.0"
    assert d["degree"] == 2
    assert d["step_count"] == 1


# ── RuntimeMetrics ───────────────────────────────────────────────────────


def test_runtime_metrics() -> None:
    m = RuntimeMetrics()
    m.record_sample("design_loop")
    m.record_sample("design_loop")
    m.record_sample("flight_sim")
    assert m.total_samples == 3
    assert m.source_counts["design_loop"] == 2
    d = m.to_dict()
    assert d["schema"] == "dark/learning_runtime_metrics/1.0"


# ── LearningRuntime ─────────────────────────────────────────────────────


def test_learning_runtime_ingest() -> None:
    rt = LearningRuntime()
    record = LearningRecord(features=[1.0, 2.0], targets=[3.0], source="test")
    loss = rt.ingest(record)
    assert loss >= 0.0
    assert rt.sample_count == 1
    assert rt.train_time_s >= 0.0


def test_learning_runtime_ingest_batch() -> None:
    rt = LearningRuntime()
    records = [
        LearningRecord(features=[float(i)], targets=[float(i * 2)], source="test")
        for i in range(10)
    ]
    losses = rt.ingest_batch(records)
    assert len(losses) == 10
    assert rt.sample_count == 10


def test_learning_runtime_fit_linear() -> None:
    rt = LearningRuntime()
    for i in range(5):
        rt.ingest(LearningRecord(features=[float(i)], targets=[float(i * 3)], source="test"))
    mse = rt.fit_linear()
    assert mse < 1.0  # Should fit well


def test_learning_runtime_predict_unified() -> None:
    rt = LearningRuntime()
    for i in range(20):
        rt.ingest(LearningRecord(features=[float(i)], targets=[float(i * 2)], source="s"))
    rt.fit_linear()
    pred = rt.predict([10.0])
    assert len(pred) == 1


def test_learning_runtime_predict_linear_only() -> None:
    rt = LearningRuntime()
    for i in range(5):
        rt.ingest(LearningRecord(features=[float(i)], targets=[float(i * 2)], source="s"))
    rt.fit_linear()
    pred = rt.predict_linear([5.0])
    assert abs(pred[0] - 10.0) < 1.0


def test_learning_runtime_predict_online_only() -> None:
    rt = LearningRuntime()
    rt.ingest(LearningRecord(features=[1.0], targets=[2.0], source="s"))
    pred = rt.predict_online([1.0])
    assert len(pred) == 1


def test_learning_runtime_register_source() -> None:
    rt = LearningRuntime()
    src = DataSource(
        name="flight_sim",
        module="reidce.flight_sim",
        feature_names=["speed", "altitude"],
        target_names=["score"],
    )
    rt.register_source(src)
    assert "flight_sim" in rt.sources


def test_learning_runtime_to_dict() -> None:
    rt = LearningRuntime()
    rt.ingest(LearningRecord(features=[1.0], targets=[2.0], source="test"))
    d = rt.to_dict()
    assert d["schema"] == "dark/learning_runtime/1.0"
    assert d["buffer_size"] == 1


def test_learning_runtime_feature_importance() -> None:
    rt = LearningRuntime()
    for i in range(10):
        rt.ingest(LearningRecord(
            features=[float(i), 0.0], targets=[float(i * 2)], source="s",
        ))
    rt.fit_linear()
    imp = rt.feature_importance
    assert len(imp) == 2
