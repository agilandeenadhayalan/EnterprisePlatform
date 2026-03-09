"""
Training Loop Components
=========================

A training loop is the core engine of machine learning: it iteratively
improves a model's parameters by:
1. Forward pass: feed data through the model to get predictions
2. Loss computation: measure how wrong the predictions are
3. Backward pass: compute gradients (direction to adjust weights)
4. Optimizer step: update weights using gradients

This module implements these components in pure Python to teach the
mechanics without requiring PyTorch or TensorFlow.

Key concepts:
- **SimpleModel**: A 2-layer neural network using matrix multiplication.
- **SGDOptimizer**: The simplest optimizer -- moves weights in the
  direction that reduces loss, scaled by learning rate.
- **MSELoss**: Mean Squared Error -- the standard regression loss.
- **EarlyStopping**: Prevents overfitting by stopping when the model
  stops improving on validation data.
- **LearningRateScheduler**: Adjusts the learning rate during training
  to balance exploration (high LR) and convergence (low LR).
"""

from __future__ import annotations

import math
import random


class SimpleModel:
    """A simple 2-layer model for teaching purposes (pure Python, no frameworks).

    Architecture:
        input (input_dim) -> hidden (hidden_dim) -> output (output_dim)

    This uses random weights and a simple ReLU-like activation. It's not
    meant to learn real patterns -- it demonstrates the mechanics of
    forward passes and parameter management.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        seed: int = 42,
    ) -> None:
        rng = random.Random(seed)

        # Xavier-like initialization: scale by 1/sqrt(fan_in)
        scale1 = 1.0 / math.sqrt(input_dim)
        scale2 = 1.0 / math.sqrt(hidden_dim)

        # Layer 1: input_dim -> hidden_dim
        self.weights1 = [
            [rng.gauss(0, scale1) for _ in range(input_dim)]
            for _ in range(hidden_dim)
        ]
        self.bias1 = [0.0] * hidden_dim

        # Layer 2: hidden_dim -> output_dim
        self.weights2 = [
            [rng.gauss(0, scale2) for _ in range(hidden_dim)]
            for _ in range(output_dim)
        ]
        self.bias2 = [0.0] * output_dim

    def forward(self, x: list[float]) -> float:
        """Forward pass: compute prediction for a single input.

        Args:
            x: Input feature vector of length input_dim.

        Returns:
            Scalar prediction (first output neuron's value).
        """
        # Layer 1: linear + ReLU activation
        hidden = []
        for i in range(len(self.weights1)):
            z = sum(w * xi for w, xi in zip(self.weights1[i], x)) + self.bias1[i]
            hidden.append(max(0.0, z))  # ReLU activation

        # Layer 2: linear (no activation for regression output)
        output = []
        for i in range(len(self.weights2)):
            z = sum(w * hi for w, hi in zip(self.weights2[i], hidden)) + self.bias2[i]
            output.append(z)

        return output[0]

    def parameters(self) -> list[list[float]]:
        """Return all model parameters as a flat list of lists.

        This is used by optimizers to know which parameters to update.
        """
        params = []
        for row in self.weights1:
            params.append(row)
        params.append(self.bias1)
        for row in self.weights2:
            params.append(row)
        params.append(self.bias2)
        return params


class SGDOptimizer:
    """Stochastic Gradient Descent optimizer.

    The simplest optimization algorithm: each parameter is updated by
    subtracting (learning_rate * gradient). This moves the parameters
    in the direction that reduces the loss.

    In this teaching implementation, we simulate gradient updates by
    applying small random perturbations scaled by the gradient direction,
    since computing true gradients for our SimpleModel would require
    a full backprop implementation.
    """

    def __init__(self, parameters: list[list[float]], lr: float = 0.01) -> None:
        """Initialize SGD optimizer.

        Args:
            parameters: References to model parameter lists.
            lr: Learning rate -- how big each update step is.
        """
        if lr <= 0:
            raise ValueError("Learning rate must be positive")
        self.parameters = parameters
        self.lr = lr
        self._gradients: list[list[float]] | None = None

    def step(self, gradients: list[list[float]]) -> None:
        """Apply one optimization step using provided gradients.

        Args:
            gradients: Gradient values matching the shape of parameters.
                       Each parameter is updated: param -= lr * gradient.
        """
        for param_list, grad_list in zip(self.parameters, gradients):
            for i in range(len(param_list)):
                param_list[i] -= self.lr * grad_list[i]

    def zero_grad(self) -> None:
        """Reset stored gradients to zero (for the next iteration)."""
        self._gradients = None


class MSELoss:
    """Mean Squared Error loss function.

    MSE = (1/n) * sum((predicted - actual)^2)

    This is the standard loss for regression problems. It penalizes
    large errors more than small ones (quadratic penalty), which
    encourages the model to avoid big mistakes.
    """

    def compute(self, predicted: list[float], actual: list[float]) -> float:
        """Compute MSE loss over a batch.

        Args:
            predicted: Model predictions.
            actual: Ground truth values.

        Returns:
            Mean squared error (always >= 0).
        """
        if len(predicted) != len(actual):
            raise ValueError("predicted and actual must have same length")
        if not predicted:
            return 0.0
        return sum((p - a) ** 2 for p, a in zip(predicted, actual)) / len(predicted)

    def gradient(self, predicted: float, actual: float) -> float:
        """Compute gradient of MSE for a single prediction.

        d/d(predicted) of (predicted - actual)^2 = 2 * (predicted - actual)

        Args:
            predicted: Single model prediction.
            actual: Single ground truth value.

        Returns:
            Gradient value (positive if predicted > actual).
        """
        return 2.0 * (predicted - actual)


class TrainingLoop:
    """Orchestrates the training process.

    A training loop ties together the model, optimizer, and loss function
    to iteratively improve the model. Each epoch:
    1. Iterates over all training data
    2. Computes predictions (forward pass)
    3. Computes loss (how wrong we are)
    4. Estimates gradients (which direction to adjust)
    5. Updates parameters (optimizer step)

    Note: This implementation uses numerical gradient estimation (finite
    differences) since implementing full backpropagation is beyond the
    scope of this teaching module.
    """

    def __init__(
        self,
        model: SimpleModel,
        optimizer: SGDOptimizer,
        loss_fn: MSELoss,
    ) -> None:
        self.model = model
        self.optimizer = optimizer
        self.loss_fn = loss_fn
        self.history: list[dict] = []

    def train_epoch(self, data: list[list[float]], labels: list[float]) -> float:
        """Train for one epoch over the data.

        Args:
            data: List of input feature vectors.
            labels: List of target values (one per input).

        Returns:
            Average loss over the epoch.
        """
        if len(data) != len(labels):
            raise ValueError("data and labels must have same length")

        total_loss = 0.0
        epsilon = 1e-5  # for numerical gradient estimation

        for x, y_true in zip(data, labels):
            # Forward pass
            y_pred = self.model.forward(x)
            loss = (y_pred - y_true) ** 2
            total_loss += loss

            # Numerical gradient estimation for each parameter
            gradients = []
            for param_list in self.model.parameters():
                grad_list = []
                for i in range(len(param_list)):
                    original = param_list[i]

                    # f(x + eps)
                    param_list[i] = original + epsilon
                    loss_plus = (self.model.forward(x) - y_true) ** 2

                    # f(x - eps)
                    param_list[i] = original - epsilon
                    loss_minus = (self.model.forward(x) - y_true) ** 2

                    # Gradient = (f(x+eps) - f(x-eps)) / (2*eps)
                    grad = (loss_plus - loss_minus) / (2 * epsilon)
                    grad_list.append(grad)

                    # Restore original value
                    param_list[i] = original

                gradients.append(grad_list)

            # Optimizer step
            self.optimizer.step(gradients)

        avg_loss = total_loss / len(data)
        return avg_loss

    def evaluate(self, data: list[list[float]], labels: list[float]) -> dict:
        """Evaluate the model on data without updating weights.

        Returns:
            Dict with 'mse', 'rmse', 'mae', and 'predictions'.
        """
        predictions = [self.model.forward(x) for x in data]
        mse = self.loss_fn.compute(predictions, labels)
        mae = sum(abs(p - a) for p, a in zip(predictions, labels)) / len(labels)

        return {
            "mse": mse,
            "rmse": math.sqrt(mse),
            "mae": mae,
            "predictions": predictions,
        }


class EarlyStopping:
    """Stops training when validation loss stops improving.

    Overfitting happens when a model memorizes training data instead of
    learning general patterns. Early stopping monitors validation loss
    and halts training when it hasn't improved for 'patience' epochs.

    This is one of the simplest and most effective regularization techniques.
    """

    def __init__(self, patience: int = 5, min_delta: float = 0.001) -> None:
        """Initialize early stopping.

        Args:
            patience: Number of epochs to wait for improvement.
            min_delta: Minimum change to qualify as an improvement.
        """
        if patience < 1:
            raise ValueError("patience must be >= 1")
        self.patience = patience
        self.min_delta = min_delta
        self._best_loss: float | None = None
        self._counter: int = 0
        self._stopped: bool = False

    def check(self, val_loss: float) -> bool:
        """Check if training should stop.

        Args:
            val_loss: Current epoch's validation loss.

        Returns:
            True if training should stop (no improvement for patience epochs).
        """
        if self._best_loss is None:
            self._best_loss = val_loss
            return False

        if val_loss < self._best_loss - self.min_delta:
            # Improvement found
            self._best_loss = val_loss
            self._counter = 0
            return False
        else:
            # No improvement
            self._counter += 1
            if self._counter >= self.patience:
                self._stopped = True
                return True
            return False

    def reset(self) -> None:
        """Reset the early stopping state."""
        self._best_loss = None
        self._counter = 0
        self._stopped = False

    @property
    def best_loss(self) -> float | None:
        """The best validation loss seen so far."""
        return self._best_loss

    @property
    def epochs_without_improvement(self) -> int:
        """Number of consecutive epochs without improvement."""
        return self._counter


class LearningRateScheduler:
    """Adjusts learning rate during training.

    WHY: A high learning rate helps explore the loss landscape early in
    training, but can overshoot the minimum later. Reducing the learning
    rate over time allows the model to converge more precisely.

    Strategies:
    - 'step': Multiply LR by a factor every N epochs.
    - 'plateau': Reduce LR when a metric stops improving.
    - 'cosine': Smoothly decay LR following a cosine curve.
    """

    def __init__(
        self,
        optimizer: SGDOptimizer,
        strategy: str = "step",
        **kwargs,
    ) -> None:
        if strategy not in ("step", "plateau", "cosine"):
            raise ValueError(f"Unknown strategy: {strategy!r}")

        self.optimizer = optimizer
        self.strategy = strategy
        self.initial_lr = optimizer.lr

        # Step decay params
        self.step_size = kwargs.get("step_size", 10)
        self.gamma = kwargs.get("gamma", 0.1)

        # Plateau params
        self.plateau_patience = kwargs.get("patience", 5)
        self.plateau_factor = kwargs.get("factor", 0.5)
        self._plateau_best: float | None = None
        self._plateau_counter: int = 0

        # Cosine params
        self.total_epochs = kwargs.get("total_epochs", 100)

    def step(self, epoch: int | None = None, metric: float | None = None) -> None:
        """Update the learning rate based on the current epoch or metric.

        Args:
            epoch: Current epoch number (required for 'step' and 'cosine').
            metric: Current metric value (required for 'plateau').
        """
        if self.strategy == "step":
            if epoch is None:
                raise ValueError("epoch is required for 'step' strategy")
            if epoch > 0 and epoch % self.step_size == 0:
                self.optimizer.lr *= self.gamma

        elif self.strategy == "plateau":
            if metric is None:
                raise ValueError("metric is required for 'plateau' strategy")
            if self._plateau_best is None or metric < self._plateau_best:
                self._plateau_best = metric
                self._plateau_counter = 0
            else:
                self._plateau_counter += 1
                if self._plateau_counter >= self.plateau_patience:
                    self.optimizer.lr *= self.plateau_factor
                    self._plateau_counter = 0
                    self._plateau_best = metric

        elif self.strategy == "cosine":
            if epoch is None:
                raise ValueError("epoch is required for 'cosine' strategy")
            # Cosine annealing: LR = initial_lr * 0.5 * (1 + cos(pi * epoch / total))
            self.optimizer.lr = (
                self.initial_lr * 0.5 * (1 + math.cos(math.pi * epoch / self.total_epochs))
            )

    def get_lr(self) -> float:
        """Return the current learning rate."""
        return self.optimizer.lr
