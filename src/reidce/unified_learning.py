"""Unified linear learning runtime for cross-module AI knowledge synthesis.

Provides a streaming learning engine that ingests data from all engineering
modules (flight sim, design loop, CAD, FEA, electromagnetic, circuitry) and
builds a continuous, incrementally-updated predictive model.  Supports both
known linear relationships (least-squares regression with closed-form
solution) and unknown/non-linear relationships (online gradient descent with
adaptive learning rate).

The runtime tracks wall-clock training time, sample counts, loss history,
and feature importance — providing full observability into what the AI is
learning and how fast.

Key components
--------------
* ``DataSource`` — labelled origin for an ingested data stream.
* ``LearningRecord`` — single observation with features, targets, source tag.
* ``LinearModel`` — closed-form least-squares linear regression with
  analytic feature importance (|β|·σ_x / σ_y).
* ``OnlineModel`` — streaming SGD model for unknown/non-linear patterns
  using polynomial feature expansion.
* ``LearningRuntime`` — orchestrator that manages both linear and online
  models, dispatches observations, and exposes a unified ``predict`` API.
* ``RuntimeMetrics`` — wall-clock timings, sample counts, loss curves.

No external dependencies — built entirely on the standard library.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

# ── Data primitives ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class DataSource:
    """Describes the origin of an ingested data stream."""

    name: str
    module: str
    feature_names: List[str]
    target_names: List[str]
    description: str = ""


@dataclass(frozen=True)
class LearningRecord:
    """Single observation from any engineering module."""

    features: List[float]
    targets: List[float]
    source: str
    timestamp_utc: float = 0.0


# ── Runtime metrics ──────────────────────────────────────────────────────


@dataclass
class RuntimeMetrics:
    """Observable metrics for the learning runtime."""

    total_samples: int = 0
    total_train_time_s: float = 0.0
    source_counts: Dict[str, int] = field(default_factory=dict)
    loss_history: List[float] = field(default_factory=list)
    linear_fit_time_s: float = 0.0
    online_steps: int = 0

    def record_sample(self, source: str) -> None:
        self.total_samples += 1
        self.source_counts[source] = self.source_counts.get(source, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "dark/learning_runtime_metrics/1.0",
            "total_samples": self.total_samples,
            "total_train_time_s": round(self.total_train_time_s, 6),
            "source_counts": dict(self.source_counts),
            "loss_history_length": len(self.loss_history),
            "final_loss": round(self.loss_history[-1], 6) if self.loss_history else None,
            "linear_fit_time_s": round(self.linear_fit_time_s, 6),
            "online_steps": self.online_steps,
        }


# ── Linear model (closed-form least-squares) ────────────────────────────


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def _mat_vec(mat: List[List[float]], vec: List[float]) -> List[float]:
    return [_dot(row, vec) for row in mat]


def _transpose(mat: List[List[float]]) -> List[List[float]]:
    if not mat:
        return []
    cols = len(mat[0])
    return [[mat[r][c] for r in range(len(mat))] for c in range(cols)]


def _mat_mul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    """Multiply two matrices (lists of row-lists)."""
    rows_a = len(a)
    cols_b = len(b[0]) if b else 0
    inner = len(b)
    result: List[List[float]] = []
    for i in range(rows_a):
        row: List[float] = []
        for j in range(cols_b):
            s = 0.0
            for k in range(inner):
                s += a[i][k] * b[k][j]
            row.append(s)
        result.append(row)
    return result


def _identity(n: int) -> List[List[float]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _solve_linear_system(
    ata: List[List[float]], atb: List[List[float]], reg: float = 1e-8
) -> List[List[float]]:
    """Solve (AᵀA + λI)β = AᵀB via Gauss-Jordan elimination."""
    n = len(ata)
    m = len(atb[0]) if atb else 0
    # Build augmented matrix [AᵀA + λI | AᵀB]
    aug: List[List[float]] = []
    for i in range(n):
        aug_row = [ata[i][j] + (reg if i == j else 0.0) for j in range(n)]
        aug_row.extend(atb[i])
        aug.append(aug_row)
    # Forward elimination with partial pivoting
    for col in range(n):
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]
        pivot = aug[col][col]
        if abs(pivot) < 1e-15:
            continue
        for j in range(n + m):
            aug[col][j] /= pivot
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            for j in range(n + m):
                aug[row][j] -= factor * aug[col][j]
    # Extract solution
    return [aug[i][n:] for i in range(n)]


@dataclass
class LinearModel:
    """Closed-form least-squares linear regression.

    Solves β = (XᵀX + λI)⁻¹ XᵀY for multi-output regression.
    Computes analytic feature importance as |β_j| · σ(x_j) / σ(y).
    """

    n_features: int = 0
    n_targets: int = 0
    coefficients: List[List[float]] = field(default_factory=list)
    intercepts: List[float] = field(default_factory=list)
    feature_importance: List[float] = field(default_factory=list)
    _fitted: bool = False

    def fit(
        self,
        x_data: Sequence[Sequence[float]],
        y_data: Sequence[Sequence[float]],
        reg: float = 1e-8,
    ) -> None:
        """Fit via closed-form normal equation."""
        n = len(x_data)
        if n == 0:
            raise ValueError("Cannot fit with zero samples.")
        self.n_features = len(x_data[0])
        self.n_targets = len(y_data[0])

        # Augment X with bias column
        x_aug = [list(row) + [1.0] for row in x_data]
        xt = _transpose(x_aug)
        xtx = _mat_mul(xt, x_aug)
        # Build XᵀY
        y_mat = [list(row) for row in y_data]
        xty = _mat_mul(xt, y_mat)

        beta = _solve_linear_system(xtx, xty, reg=reg)
        self.coefficients = [beta[j] for j in range(self.n_features)]
        self.intercepts = beta[self.n_features]

        # Compute feature importance
        self._compute_importance(x_data, y_data)
        self._fitted = True

    def _compute_importance(
        self,
        x_data: Sequence[Sequence[float]],
        y_data: Sequence[Sequence[float]],
    ) -> None:
        """Feature importance = mean |β_j| · σ(x_j) / mean(σ(y_k))."""
        n = len(x_data)
        if n < 2:
            self.feature_importance = [0.0] * self.n_features
            return

        # Compute std of each feature
        x_means = [0.0] * self.n_features
        for row in x_data:
            for j in range(self.n_features):
                x_means[j] += row[j]
        x_means = [m / n for m in x_means]

        x_std = [0.0] * self.n_features
        for row in x_data:
            for j in range(self.n_features):
                x_std[j] += (row[j] - x_means[j]) ** 2
        x_std = [math.sqrt(s / max(n - 1, 1)) for s in x_std]

        # Compute mean std of targets
        y_means = [0.0] * self.n_targets
        for row in y_data:
            for k in range(self.n_targets):
                y_means[k] += row[k]
        y_means = [m / n for m in y_means]

        y_std = [0.0] * self.n_targets
        for row in y_data:
            for k in range(self.n_targets):
                y_std[k] += (row[k] - y_means[k]) ** 2
        y_std_mean = sum(math.sqrt(s / max(n - 1, 1)) for s in y_std) / max(self.n_targets, 1)

        if y_std_mean < 1e-15:
            self.feature_importance = [0.0] * self.n_features
            return

        importance: List[float] = []
        for j in range(self.n_features):
            mean_abs_beta = sum(abs(self.coefficients[j][k]) for k in range(self.n_targets))
            mean_abs_beta /= max(self.n_targets, 1)
            importance.append(round(mean_abs_beta * x_std[j] / y_std_mean, 6))
        self.feature_importance = importance

    def predict(self, features: Sequence[float]) -> List[float]:
        if not self._fitted:
            raise RuntimeError("LinearModel has not been fitted.")
        result: List[float] = []
        for k in range(self.n_targets):
            val = self.intercepts[k]
            for j in range(self.n_features):
                val += self.coefficients[j][k] * features[j]
            result.append(val)
        return result

    def predict_batch(
        self, features_batch: Sequence[Sequence[float]]
    ) -> List[List[float]]:
        return [self.predict(row) for row in features_batch]

    def residual_mse(
        self,
        x_data: Sequence[Sequence[float]],
        y_data: Sequence[Sequence[float]],
    ) -> float:
        """Compute mean squared error on given data."""
        if not self._fitted:
            raise RuntimeError("LinearModel has not been fitted.")
        total = 0.0
        n = len(x_data)
        for i in range(n):
            pred = self.predict(x_data[i])
            for k in range(self.n_targets):
                total += (pred[k] - y_data[i][k]) ** 2
        return total / max(n * self.n_targets, 1)

    def is_fitted(self) -> bool:
        return self._fitted

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "dark/linear_model/1.0",
            "n_features": self.n_features,
            "n_targets": self.n_targets,
            "coefficients": self.coefficients,
            "intercepts": self.intercepts,
            "feature_importance": self.feature_importance,
            "fitted": self._fitted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LinearModel:
        return cls(
            n_features=data["n_features"],
            n_targets=data["n_targets"],
            coefficients=data["coefficients"],
            intercepts=data["intercepts"],
            feature_importance=data.get("feature_importance", []),
            _fitted=data.get("fitted", False),
        )


# ── Online model (streaming SGD with polynomial expansion) ──────────────


def _polynomial_features(
    x: Sequence[float], degree: int = 2
) -> List[float]:
    """Expand features to include polynomial interactions up to *degree*.

    For degree=2 with features [a, b]: returns [a, b, a², ab, b²].
    """
    base = list(x)
    if degree < 2:
        return base
    expanded = list(base)
    n = len(base)
    for i in range(n):
        for j in range(i, n):
            expanded.append(base[i] * base[j])
    return expanded


@dataclass
class OnlineModel:
    """Streaming online learning model with SGD.

    Supports polynomial feature expansion to capture unknown non-linear
    patterns while maintaining O(1) memory per update step.
    """

    n_raw_features: int = 0
    n_targets: int = 0
    degree: int = 2
    weights: List[List[float]] = field(default_factory=list)
    biases: List[float] = field(default_factory=list)
    learning_rate: float = 0.001
    _n_expanded: int = 0
    _step_count: int = 0
    _initialized: bool = False

    def _init_weights(self, n_raw: int, n_targets: int) -> None:
        self.n_raw_features = n_raw
        self.n_targets = n_targets
        sample = _polynomial_features([0.0] * n_raw, self.degree)
        self._n_expanded = len(sample)
        self.weights = [[0.0] * self._n_expanded for _ in range(n_targets)]
        self.biases = [0.0] * n_targets
        self._initialized = True

    def partial_fit(
        self,
        features: Sequence[float],
        targets: Sequence[float],
    ) -> float:
        """One SGD step on a single observation. Returns squared error."""
        if not self._initialized:
            self._init_weights(len(features), len(targets))

        expanded = _polynomial_features(features, self.degree)
        # Clip expanded features to prevent numerical overflow
        clipped = [max(-1e6, min(1e6, v)) for v in expanded]
        # Forward
        preds = [
            self.biases[k] + _dot(self.weights[k], clipped)
            for k in range(self.n_targets)
        ]
        # Error
        errors = [preds[k] - targets[k] for k in range(self.n_targets)]
        loss = sum(e * e for e in errors) / max(self.n_targets, 1)

        # Adaptive learning rate: scale down by gradient magnitude
        grad_norm = sum(e * e for e in errors)
        adaptive_lr = self.learning_rate / (1.0 + grad_norm * 1e-6)

        # SGD update
        for k in range(self.n_targets):
            grad = 2.0 * errors[k] / max(self.n_targets, 1)
            self.biases[k] -= adaptive_lr * grad
            for j in range(self._n_expanded):
                self.weights[k][j] -= adaptive_lr * grad * clipped[j]

        self._step_count += 1
        return loss

    def predict(self, features: Sequence[float]) -> List[float]:
        if not self._initialized:
            raise RuntimeError("OnlineModel has not been initialized.")
        expanded = _polynomial_features(features, self.degree)
        return [
            self.biases[k] + _dot(self.weights[k], expanded)
            for k in range(self.n_targets)
        ]

    def is_initialized(self) -> bool:
        return self._initialized

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "dark/online_model/1.0",
            "n_raw_features": self.n_raw_features,
            "n_targets": self.n_targets,
            "degree": self.degree,
            "step_count": self._step_count,
            "initialized": self._initialized,
        }


# ── Learning runtime ─────────────────────────────────────────────────────


@dataclass
class LearningRuntime:
    """Unified learning runtime that manages linear and online models.

    Ingests ``LearningRecord`` observations from any engineering module,
    dispatches them to the appropriate model (linear for batch/known
    relationships, online for streaming/unknown), and provides a
    unified prediction interface.

    The runtime tracks wall-clock training time, sample counts, and
    loss history for full observability.
    """

    sources: Dict[str, DataSource] = field(default_factory=dict)
    linear_model: LinearModel = field(default_factory=LinearModel)
    online_model: OnlineModel = field(default_factory=OnlineModel)
    metrics: RuntimeMetrics = field(default_factory=RuntimeMetrics)
    _buffer_x: List[List[float]] = field(default_factory=list)
    _buffer_y: List[List[float]] = field(default_factory=list)
    _buffer_limit: int = 256

    def register_source(self, source: DataSource) -> None:
        """Register a data source for ingestion."""
        self.sources[source.name] = source

    def ingest(self, record: LearningRecord) -> float:
        """Ingest a single observation.

        The record is simultaneously buffered for periodic linear
        re-fit and streamed to the online model for immediate
        incremental learning.

        Returns the online model's loss for this observation.
        """
        t0 = time.monotonic()
        self.metrics.record_sample(record.source)

        # Buffer for linear model
        self._buffer_x.append(list(record.features))
        self._buffer_y.append(list(record.targets))

        # Online step
        loss = self.online_model.partial_fit(record.features, record.targets)
        self.metrics.loss_history.append(loss)
        self.metrics.online_steps += 1

        elapsed = time.monotonic() - t0
        self.metrics.total_train_time_s += elapsed
        return loss

    def ingest_batch(self, records: Sequence[LearningRecord]) -> List[float]:
        """Ingest a batch of observations."""
        return [self.ingest(r) for r in records]

    def fit_linear(self, reg: float = 1e-8) -> float:
        """Re-fit the linear model on all buffered data.

        Returns the residual MSE of the linear model on the buffer.
        """
        if not self._buffer_x:
            raise ValueError("No buffered data for linear fit.")
        t0 = time.monotonic()
        self.linear_model.fit(self._buffer_x, self._buffer_y, reg=reg)
        elapsed = time.monotonic() - t0
        self.metrics.linear_fit_time_s += elapsed
        self.metrics.total_train_time_s += elapsed
        return self.linear_model.residual_mse(self._buffer_x, self._buffer_y)

    def predict_linear(self, features: Sequence[float]) -> List[float]:
        """Predict using the closed-form linear model."""
        return self.linear_model.predict(features)

    def predict_online(self, features: Sequence[float]) -> List[float]:
        """Predict using the streaming online model."""
        return self.online_model.predict(features)

    def predict(self, features: Sequence[float]) -> List[float]:
        """Unified prediction: prefers linear when fitted, falls back to online.

        When both models are available, uses weighted combination where the
        linear model (closed-form) is weighted more heavily than the online
        (streaming SGD) model since the analytical solution is more stable.
        """
        have_linear = self.linear_model.is_fitted()
        have_online = self.online_model.is_initialized()
        if have_linear and have_online:
            lin = self.linear_model.predict(features)
            onl = self.online_model.predict(features)
            # Weight linear model 80%, online 20% — analytical is more stable
            return [0.8 * a + 0.2 * b for a, b in zip(lin, onl, strict=False)]
        if have_linear:
            return self.linear_model.predict(features)
        if have_online:
            return self.online_model.predict(features)
        raise RuntimeError("No models have been trained yet.")

    @property
    def feature_importance(self) -> List[float]:
        """Feature importance from the linear model."""
        return self.linear_model.feature_importance

    @property
    def sample_count(self) -> int:
        return self.metrics.total_samples

    @property
    def train_time_s(self) -> float:
        return self.metrics.total_train_time_s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "dark/learning_runtime/1.0",
            "sources": list(self.sources.keys()),
            "metrics": self.metrics.to_dict(),
            "linear_model": self.linear_model.to_dict(),
            "online_model": self.online_model.to_dict(),
            "buffer_size": len(self._buffer_x),
        }


# ── Convenience: cross-module data collection ────────────────────────────


def build_runtime_from_design_loop(
    log: Any,
    source_name: str = "design_loop",
) -> LearningRuntime:
    """Create a ``LearningRuntime`` pre-loaded with design-loop data.

    Accepts an ``IterationLog`` from ``design_loop.py`` and ingests
    all iterations as training data.
    """
    from reidce.design_loop import collect_training_data

    x_data, y_data = collect_training_data(log)
    runtime = LearningRuntime()
    runtime.register_source(DataSource(
        name=source_name,
        module="reidce.design_loop",
        feature_names=[
            "mass_kg", "wing_area_m2", "cd0",
            "max_thrust_n", "max_tilt_rad", "max_speed_m_s",
        ],
        target_names=[
            "design_score", "max_altitude_m", "max_speed_achieved_m_s",
            "sustained_turn_rate_deg_s", "min_battery_pct",
        ],
    ))
    records = [
        LearningRecord(features=x, targets=y, source=source_name)
        for x, y in zip(x_data, y_data, strict=False)
    ]
    runtime.ingest_batch(records)
    if records:
        runtime.fit_linear()
    return runtime
