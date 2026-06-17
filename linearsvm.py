from __future__ import annotations

import math
import random
import time
from typing import Any, Iterable, Sequence


try:
    import cupy as cp
except ImportError:
    cp = None


class LinearSVM:
    """Linear Support Vector Machine without scikit-learn.

    The model is trained with mini-batch gradient descent on this objective:

        0.5 * ||w||^2 + C * mean(max(0, 1 - y * (w.x + b)))

    It supports binary classification only. Labels can be numbers or strings;
    internally they are mapped to -1 and +1. The CPU backend is pure Python.
    The optional GPU backend uses CuPy for matrix operations.
    """

    def __init__(
        self,
        C: float = 1.0,
        learning_rate: float = 0.01,
        epochs: int = 1000,
        batch_size: int | None = None,
        fit_intercept: bool = True,
        standardize: bool = True,
        shuffle: bool = True,
        random_state: int | None = None,
        tol: float = 1e-6,
        n_iter_no_change: int = 20,
        device: str = "cpu",
    ) -> None:
        if C <= 0:
            raise ValueError("C must be positive.")
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive.")
        if epochs <= 0:
            raise ValueError("epochs must be positive.")
        if batch_size is not None and batch_size <= 0:
            raise ValueError("batch_size must be positive or None.")
        if device not in {"cpu", "gpu", "auto"}:
            raise ValueError("device must be 'cpu', 'gpu', or 'auto'.")

        self.C = C
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.fit_intercept = fit_intercept
        self.standardize = standardize
        self.shuffle = shuffle
        self.random_state = random_state
        self.tol = tol
        self.n_iter_no_change = n_iter_no_change
        self.device = device

        self.weights_: list[float] | None = None
        self.bias_: float = 0.0
        self.classes_: tuple[Any, Any] | None = None
        self.mean_: list[float] | None = None
        self.scale_: list[float] | None = None
        self.loss_history_: list[float] = []
        self.training_time_: float = 0.0
        self.n_epochs_: int = 0
        self.backend_: str = "cpu"

    def fit(self, X: Sequence[Sequence[float]], y: Sequence[Any]) -> "LinearSVM":
        X_train = self._validate_X(X)
        y_values = list(y)

        if len(X_train) != len(y_values):
            raise ValueError("X and y must have the same number of samples.")

        classes = sorted(set(y_values), key=repr)
        if len(classes) != 2:
            raise ValueError("LinearSVM only supports binary classification.")

        self.classes_ = (classes[0], classes[1])
        y_signed = [-1.0 if label == classes[0] else 1.0 for label in y_values]

        if self._should_use_gpu():
            return self._fit_gpu(X_train, y_signed)

        X_scaled = self._fit_transform_X(X_train)

        n_samples = len(X_scaled)
        n_features = len(X_scaled[0])
        batch_size = self.batch_size or n_samples
        rng = random.Random(self.random_state)

        self.weights_ = [0.0] * n_features
        self.bias_ = 0.0
        self.loss_history_ = []
        self.training_time_ = 0.0
        self.n_epochs_ = 0
        self.backend_ = "cpu"

        best_loss = math.inf
        epochs_without_change = 0
        start_time = time.perf_counter()

        for epoch in range(self.epochs):
            indices = list(range(n_samples))
            if self.shuffle:
                rng.shuffle(indices)

            for start in range(0, n_samples, batch_size):
                batch_idx = indices[start : start + batch_size]
                X_batch = [X_scaled[i] for i in batch_idx]
                y_batch = [y_signed[i] for i in batch_idx]
                self._gradient_step(X_batch, y_batch)

            loss = self._loss(X_scaled, y_signed)
            self.loss_history_.append(loss)

            if best_loss - loss > self.tol:
                best_loss = loss
                epochs_without_change = 0
            else:
                epochs_without_change += 1

            if epochs_without_change >= self.n_iter_no_change:
                break

        self.n_epochs_ = epoch + 1
        self.training_time_ = time.perf_counter() - start_time
        return self

    def predict(self, X: Sequence[Sequence[float]]) -> list[Any]:
        self._check_is_fitted()
        assert self.classes_ is not None

        scores = self.decision_function(X)
        return [self.classes_[1] if score >= 0 else self.classes_[0] for score in scores]

    def decision_function(self, X: Sequence[Sequence[float]]) -> list[float]:
        self._check_is_fitted()
        assert self.weights_ is not None

        X_values = self._validate_X(X)
        if self.backend_ == "gpu" and cp is not None:
            return self._decision_function_gpu(X_values)

        X_scaled = self._transform_X(X_values)
        return [self._dot(row, self.weights_) + self.bias_ for row in X_scaled]

    def _fit_gpu(self, X: list[list[float]], y: list[float]) -> "LinearSVM":
        if cp is None:
            raise RuntimeError(
                "CuPy is required for GPU training. Install a CUDA-matched package, "
                "for example: pip install cupy-cuda12x"
            )

        start_time = time.perf_counter()
        X_gpu = cp.asarray(X, dtype=cp.float64)
        y_gpu = cp.asarray(y, dtype=cp.float64)

        if self.standardize:
            mean_gpu = cp.mean(X_gpu, axis=0)
            scale_gpu = cp.std(X_gpu, axis=0)
            scale_gpu = cp.where(scale_gpu == 0.0, 1.0, scale_gpu)
            X_gpu = (X_gpu - mean_gpu) / scale_gpu
        else:
            n_features = X_gpu.shape[1]
            mean_gpu = cp.zeros(n_features, dtype=cp.float64)
            scale_gpu = cp.ones(n_features, dtype=cp.float64)

        n_samples, n_features = X_gpu.shape
        batch_size = self.batch_size or n_samples
        rng = random.Random(self.random_state)

        weights_gpu = cp.zeros(n_features, dtype=cp.float64)
        bias_gpu = cp.asarray(0.0, dtype=cp.float64)
        self.loss_history_ = []
        self.training_time_ = 0.0
        self.n_epochs_ = 0
        self.backend_ = "gpu"

        best_loss = math.inf
        epochs_without_change = 0

        for epoch in range(self.epochs):
            indices = list(range(n_samples))
            if self.shuffle:
                rng.shuffle(indices)

            for start in range(0, n_samples, batch_size):
                batch_idx = cp.asarray(indices[start : start + batch_size], dtype=cp.int64)
                X_batch = X_gpu[batch_idx]
                y_batch = y_gpu[batch_idx]

                margins = y_batch * (X_batch @ weights_gpu + bias_gpu)
                violating = margins < 1.0
                active_targets = cp.where(violating, y_batch, 0.0)

                grad_w = weights_gpu - self.C * (X_batch.T @ active_targets) / X_batch.shape[0]
                grad_b = 0.0
                if self.fit_intercept:
                    grad_b = -self.C * cp.sum(active_targets) / X_batch.shape[0]

                weights_gpu -= self.learning_rate * grad_w
                if self.fit_intercept:
                    bias_gpu -= self.learning_rate * grad_b

            margins = y_gpu * (X_gpu @ weights_gpu + bias_gpu)
            hinge_loss = cp.maximum(0.0, 1.0 - margins)
            regularization = 0.5 * cp.dot(weights_gpu, weights_gpu)
            loss = float((regularization + self.C * cp.mean(hinge_loss)).get())
            self.loss_history_.append(loss)

            if best_loss - loss > self.tol:
                best_loss = loss
                epochs_without_change = 0
            else:
                epochs_without_change += 1

            if epochs_without_change >= self.n_iter_no_change:
                break

        cp.cuda.Stream.null.synchronize()
        self.weights_ = cp.asnumpy(weights_gpu).tolist()
        self.bias_ = float(bias_gpu.get())
        self.mean_ = cp.asnumpy(mean_gpu).tolist()
        self.scale_ = cp.asnumpy(scale_gpu).tolist()
        self.n_epochs_ = epoch + 1
        self.training_time_ = time.perf_counter() - start_time
        return self

    def _decision_function_gpu(self, X: list[list[float]]) -> list[float]:
        assert self.weights_ is not None
        assert self.mean_ is not None
        assert self.scale_ is not None

        X_gpu = cp.asarray(X, dtype=cp.float64)
        weights_gpu = cp.asarray(self.weights_, dtype=cp.float64)
        mean_gpu = cp.asarray(self.mean_, dtype=cp.float64)
        scale_gpu = cp.asarray(self.scale_, dtype=cp.float64)

        scores_gpu = ((X_gpu - mean_gpu) / scale_gpu) @ weights_gpu + self.bias_
        cp.cuda.Stream.null.synchronize()
        return cp.asnumpy(scores_gpu).tolist()

    def score(self, X: Sequence[Sequence[float]], y: Sequence[Any]) -> float:
        predictions = self.predict(X)
        y_values = list(y)
        if len(predictions) != len(y_values):
            raise ValueError("X and y must have the same number of samples.")
        correct = sum(pred == target for pred, target in zip(predictions, y_values))
        return correct / len(y_values)

    def _gradient_step(self, X: list[list[float]], y: list[float]) -> None:
        assert self.weights_ is not None

        batch_size = len(X)
        grad_w = self.weights_[:]
        grad_b = 0.0

        for row, target in zip(X, y):
            margin = target * (self._dot(row, self.weights_) + self.bias_)
            if margin < 1.0:
                for j, value in enumerate(row):
                    grad_w[j] -= self.C * target * value / batch_size
                if self.fit_intercept:
                    grad_b -= self.C * target / batch_size

        for j, gradient in enumerate(grad_w):
            self.weights_[j] -= self.learning_rate * gradient
        if self.fit_intercept:
            self.bias_ -= self.learning_rate * grad_b

    def _loss(self, X: list[list[float]], y: list[float]) -> float:
        assert self.weights_ is not None

        hinge_sum = 0.0
        for row, target in zip(X, y):
            margin = target * (self._dot(row, self.weights_) + self.bias_)
            hinge_sum += max(0.0, 1.0 - margin)

        regularization = 0.5 * self._dot(self.weights_, self.weights_)
        return regularization + self.C * hinge_sum / len(X)

    def _fit_transform_X(self, X: list[list[float]]) -> list[list[float]]:
        n_features = len(X[0])

        if not self.standardize:
            self.mean_ = [0.0] * n_features
            self.scale_ = [1.0] * n_features
            return [row[:] for row in X]

        self.mean_ = []
        self.scale_ = []

        for j in range(n_features):
            column = [row[j] for row in X]
            mean = sum(column) / len(column)
            variance = sum((value - mean) ** 2 for value in column) / len(column)
            scale = math.sqrt(variance) or 1.0
            self.mean_.append(mean)
            self.scale_.append(scale)

        return self._transform_X(X)

    def _transform_X(self, X: list[list[float]]) -> list[list[float]]:
        assert self.mean_ is not None
        assert self.scale_ is not None

        return [
            [(value - self.mean_[j]) / self.scale_[j] for j, value in enumerate(row)]
            for row in X
        ]

    def _validate_X(self, X: Sequence[Sequence[float]]) -> list[list[float]]:
        rows = [list(row) for row in X]
        if not rows:
            raise ValueError("X must not be empty.")

        n_features = len(rows[0])
        if n_features == 0:
            raise ValueError("X must have at least one feature.")

        for row in rows:
            if len(row) != n_features:
                raise ValueError("All rows in X must have the same number of features.")
            for value in row:
                if not isinstance(value, (int, float)):
                    raise ValueError("All feature values in X must be numeric.")

        return [[float(value) for value in row] for row in rows]

    def _check_is_fitted(self) -> None:
        if self.weights_ is None or self.classes_ is None:
            raise RuntimeError("Call fit(X, y) before prediction.")

    def _should_use_gpu(self) -> bool:
        if self.device == "cpu":
            return False
        if cp is None:
            if self.device == "gpu":
                raise RuntimeError(
                    "device='gpu' was requested, but CuPy is not installed. "
                    "Install a CUDA-matched package, for example: pip install cupy-cuda12x"
                )
            return False

        try:
            return cp.cuda.runtime.getDeviceCount() > 0
        except Exception as exc:
            if self.device == "gpu":
                raise RuntimeError("device='gpu' was requested, but no CUDA GPU is available.") from exc
            return False

    @staticmethod
    def _dot(a: Iterable[float], b: Iterable[float]) -> float:
        return sum(x * y for x, y in zip(a, b))


if __name__ == "__main__":
    total_start_time = time.perf_counter()

    rng = random.Random(42)
    true_weights = [1.8, -2.4, 0.9, 1.2, -1.5, 0.7, -0.8, 1.1, -0.4, 0.6]
    X_demo = []
    y_demo = []

    for i in range(1000):
        row = [rng.gauss(0.0, 1.0) for _ in range(10)]

        # Add weak nonlinear-looking interactions into existing linear features.
        row[2] += 0.35 * row[0] * row[1]
        row[5] += 0.25 * (row[3] ** 2 - 1.0)
        row[8] += 0.15 * math.sin(row[4])

        score = sum(value * weight for value, weight in zip(row, true_weights))
        score += 0.8 * math.sin(i / 19.0)
        score += rng.gauss(0.0, 1.2)

        label = 1 if score >= 0.0 else 0
        if rng.random() < 0.04:
            label = 1 - label

        X_demo.append(row)
        y_demo.append(label)

    model = LinearSVM(
        C=3.0,
        learning_rate=0.005,
        epochs=3000,
        batch_size=64,
        random_state=42,
        n_iter_no_change=80,
        device="auto",
    )
    model.fit(X_demo, y_demo)

    prediction_start_time = time.perf_counter()
    predictions = model.predict(X_demo)
    prediction_time = time.perf_counter() - prediction_start_time

    total_execution_time = time.perf_counter() - total_start_time

    print("Samples:", len(X_demo))
    print("Features:", len(X_demo[0]))
    print("Backend:", model.backend_)
    print("First 20 predictions:", predictions[:20])
    print("Accuracy:", model.score(X_demo, y_demo))
    print("Weights:", model.weights_)
    print("Bias:", model.bias_)
    print("Epochs run:", model.n_epochs_)
    print(f"Training time: {model.training_time_:.6f} seconds")
    print(f"Prediction time: {prediction_time:.6f} seconds")
    print(f"Total execution time: {total_execution_time:.6f} seconds")
