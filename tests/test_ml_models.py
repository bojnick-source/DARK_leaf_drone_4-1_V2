"""Tests for reidce.ml_models — machine learning and deep learning."""

import math
from pathlib import Path

from reidce.ml_models import (
    DenseLayer,
    FeatureScaler,
    FeedForwardNetwork,
    SurrogateModel,
    build_design_surrogate,
)

# ── FeatureScaler ────────────────────────────────────────────────────────


def test_feature_scaler_fit_transform() -> None:
    scaler = FeatureScaler()
    data = [[0.0, 10.0], [1.0, 20.0], [2.0, 30.0]]
    scaler.fit(data)
    assert scaler.mins == [0.0, 10.0]
    assert scaler.maxs == [2.0, 30.0]

    scaled = scaler.transform([1.0, 20.0])
    assert abs(scaled[0] - 0.5) < 1e-9
    assert abs(scaled[1] - 0.5) < 1e-9


def test_feature_scaler_inverse_transform() -> None:
    scaler = FeatureScaler()
    scaler.fit([[0.0, 100.0], [10.0, 200.0]])
    scaled = scaler.transform([5.0, 150.0])
    recovered = scaler.inverse_transform(scaled)
    assert abs(recovered[0] - 5.0) < 1e-9
    assert abs(recovered[1] - 150.0) < 1e-9


def test_feature_scaler_constant_column() -> None:
    """Constant feature should map to 0.5."""
    scaler = FeatureScaler()
    scaler.fit([[3.0], [3.0], [3.0]])
    assert scaler.transform([3.0]) == [0.5]


def test_feature_scaler_serialization() -> None:
    scaler = FeatureScaler()
    scaler.fit([[1.0, 2.0], [3.0, 4.0]])
    data = scaler.to_dict()
    loaded = FeatureScaler.from_dict(data)
    assert loaded.mins == scaler.mins
    assert loaded.maxs == scaler.maxs


# ── DenseLayer ───────────────────────────────────────────────────────────


def test_dense_layer_create_dimensions() -> None:
    layer = DenseLayer.create(3, 5, seed=0)
    assert layer.n_in == 3
    assert layer.n_out == 5
    assert len(layer.weights) == 5
    assert len(layer.weights[0]) == 3


def test_dense_layer_forward_output_length() -> None:
    layer = DenseLayer.create(2, 3, seed=0)
    activated, pre = layer.forward([1.0, 2.0])
    assert len(activated) == 3
    assert len(pre) == 3


def test_dense_layer_relu_non_negative() -> None:
    layer = DenseLayer.create(2, 4, use_relu=True, seed=0)
    activated, _ = layer.forward([-10.0, -10.0])
    for val in activated:
        assert val >= 0.0


def test_dense_layer_linear_output() -> None:
    layer = DenseLayer.create(2, 3, use_relu=False, seed=0)
    activated, pre = layer.forward([1.0, 2.0])
    assert activated == pre


def test_dense_layer_serialization() -> None:
    layer = DenseLayer.create(3, 2, seed=7)
    data = layer.to_dict()
    loaded = DenseLayer.from_dict(data)
    assert loaded.weights == layer.weights
    assert loaded.biases == layer.biases
    assert loaded.use_relu == layer.use_relu


# ── FeedForwardNetwork ───────────────────────────────────────────────────


def test_network_create_layer_count() -> None:
    net = FeedForwardNetwork.create([4, 8, 4, 1], seed=0)
    assert len(net.layers) == 3


def test_network_predict_output_size() -> None:
    net = FeedForwardNetwork.create([3, 8, 2], seed=0)
    output = net.predict([1.0, 2.0, 3.0])
    assert len(output) == 2


def test_network_train_step_reduces_loss() -> None:
    """A single training step should reduce loss on the training sample."""
    net = FeedForwardNetwork.create([2, 8, 1], seed=42)
    x = [[1.0, 0.0], [0.0, 1.0]]
    y = [[1.0], [0.0]]
    loss1 = net.train_step(x, y, learning_rate=0.01)
    loss2 = net.train_step(x, y, learning_rate=0.01)
    # Loss should decrease (or stay very small)
    assert loss2 <= loss1 + 1e-6


def test_network_serialization_roundtrip() -> None:
    net = FeedForwardNetwork.create([2, 4, 1], seed=0)
    data = net.to_dict()
    loaded = FeedForwardNetwork.from_dict(data)
    input_vec = [0.5, 0.5]
    assert net.predict(input_vec) == loaded.predict(input_vec)


def test_network_backprop_gradients_finite() -> None:
    net = FeedForwardNetwork.create([2, 4, 1], seed=0)
    wg, bg, loss = net._backprop([1.0, 2.0], [1.0])
    assert math.isfinite(loss)
    for layer_grads in wg:
        for row in layer_grads:
            for val in row:
                assert math.isfinite(val)


# ── SurrogateModel ───────────────────────────────────────────────────────


def _make_training_data():
    """Synthetic engineering data: y ≈ x1 + 2*x2."""
    x_data = [[float(i), float(j)] for i in range(5) for j in range(5)]
    y_data = [[row[0] + 2.0 * row[1]] for row in x_data]
    return x_data, y_data


def test_surrogate_train_and_predict() -> None:
    x, y = _make_training_data()
    model = SurrogateModel(
        feature_names=["x1", "x2"],
        target_names=["y"],
        _hidden_sizes=[8],
        _seed=42,
    )
    history = model.train(x, y, epochs=100, learning_rate=0.05)
    assert model.is_trained()
    assert len(history.epoch_losses) == 100
    assert history.final_loss < history.epoch_losses[0]

    pred = model.predict([2.0, 3.0])
    assert "y" in pred


def test_surrogate_save_load(tmp_path: Path) -> None:
    x, y = _make_training_data()
    model = SurrogateModel(
        feature_names=["x1", "x2"],
        target_names=["y"],
        _hidden_sizes=[8],
        _seed=42,
    )
    model.train(x, y, epochs=50)

    path = tmp_path / "model.json"
    model.save(path)
    assert path.exists()

    loaded = SurrogateModel.load(path)
    assert loaded.is_trained()
    assert loaded.feature_names == model.feature_names
    assert loaded.target_names == model.target_names

    # Predictions should match
    original = model.predict([1.0, 1.0])
    restored = loaded.predict([1.0, 1.0])
    for key in original:
        assert abs(original[key] - restored[key]) < 1e-6


def test_surrogate_predict_batch() -> None:
    x, y = _make_training_data()
    model = SurrogateModel(
        feature_names=["x1", "x2"],
        target_names=["y"],
        _hidden_sizes=[8],
        _seed=42,
    )
    model.train(x, y, epochs=50)
    batch = [[0.0, 0.0], [1.0, 1.0], [4.0, 4.0]]
    results = model.predict_batch(batch)
    assert len(results) == 3
    for r in results:
        assert "y" in r


def test_surrogate_to_dict() -> None:
    model = SurrogateModel(
        feature_names=["a", "b"],
        target_names=["c"],
    )
    d = model.to_dict()
    assert d["schema"] == "dark/surrogate_model/1.0"
    assert d["trained"] is False


def test_surrogate_untrained_predict_raises() -> None:
    model = SurrogateModel(
        feature_names=["a"], target_names=["b"],
    )
    try:
        model.predict([1.0])
        raise AssertionError("Expected RuntimeError")
    except RuntimeError:
        pass


def test_surrogate_empty_data_raises() -> None:
    model = SurrogateModel(
        feature_names=["a"], target_names=["b"],
    )
    try:
        model.train([], [])
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


# ── build_design_surrogate ───────────────────────────────────────────────


def test_build_design_surrogate_defaults() -> None:
    surrogate = build_design_surrogate()
    assert len(surrogate.feature_names) == 6
    assert len(surrogate.target_names) == 5
    assert not surrogate.is_trained()


def test_build_design_surrogate_custom_hidden() -> None:
    surrogate = build_design_surrogate(hidden_sizes=[32, 16, 8])
    assert surrogate._hidden_sizes == [32, 16, 8]
