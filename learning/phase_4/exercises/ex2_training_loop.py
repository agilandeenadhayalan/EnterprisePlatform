"""
Exercise 2: Training Loop Implementation
==========================================

CONCEPT:
A training loop is the engine of machine learning. Each epoch, it:
1. Forward pass: run data through the model to get predictions.
2. Loss computation: measure how wrong the predictions are.
3. Gradient estimation: figure out which direction to adjust weights.
4. Optimizer step: actually adjust the weights.

After training, evaluation runs the model on held-out data WITHOUT
updating weights to measure generalization.

YOUR TASK:
Implement two methods:
- train_one_epoch(): The core training loop over one pass of the data.
- evaluate(): Run the model on test data and compute metrics.

You are given a SimpleModel, MSELoss, and SGDOptimizer that are already
implemented. You just need to wire them together in the training loop.

HINTS:
- For gradient estimation, use numerical differentiation (finite differences):
  gradient = (loss(param + eps) - loss(param - eps)) / (2 * eps)
- This is slow but conceptually simple -- real frameworks use automatic
  differentiation (backpropagation) instead.
"""

import math
import random


# --- Provided implementations (do NOT modify) ---

class SimpleModel:
    """A simple 2-layer model (provided -- do not modify)."""

    def __init__(self, input_dim: int, hidden_dim: int, seed: int = 42) -> None:
        rng = random.Random(seed)
        scale = 1.0 / math.sqrt(input_dim)
        self.weights = [
            [rng.gauss(0, scale) for _ in range(input_dim)]
            for _ in range(hidden_dim)
        ]
        self.bias = [0.0] * hidden_dim
        self.output_weights = [rng.gauss(0, 0.1) for _ in range(hidden_dim)]

    def forward(self, x: list[float]) -> float:
        hidden = []
        for i in range(len(self.weights)):
            z = sum(w * xi for w, xi in zip(self.weights[i], x)) + self.bias[i]
            hidden.append(max(0.0, z))
        return sum(w * h for w, h in zip(self.output_weights, hidden))

    def parameters(self) -> list[list[float]]:
        params = []
        for row in self.weights:
            params.append(row)
        params.append(self.bias)
        params.append(self.output_weights)
        return params


class MSELoss:
    """Mean Squared Error (provided -- do not modify)."""

    def compute(self, predicted: list[float], actual: list[float]) -> float:
        return sum((p - a) ** 2 for p, a in zip(predicted, actual)) / len(predicted)


class SGDOptimizer:
    """Stochastic Gradient Descent (provided -- do not modify)."""

    def __init__(self, parameters: list[list[float]], lr: float = 0.01) -> None:
        self.parameters = parameters
        self.lr = lr

    def step(self, gradients: list[list[float]]) -> None:
        for param_list, grad_list in zip(self.parameters, gradients):
            for i in range(len(param_list)):
                param_list[i] -= self.lr * grad_list[i]


# --- Your implementation ---

class TrainingLoop:
    """Orchestrates training: forward pass, loss, gradient, optimizer step."""

    def __init__(
        self,
        model: SimpleModel,
        optimizer: SGDOptimizer,
        loss_fn: MSELoss,
    ) -> None:
        self.model = model
        self.optimizer = optimizer
        self.loss_fn = loss_fn

    def train_one_epoch(
        self,
        data: list[list[float]],
        labels: list[float],
    ) -> float:
        """Train for one epoch over all data points.

        For each (x, y_true) pair:
        1. Compute y_pred = model.forward(x)
        2. Compute loss = (y_pred - y_true)^2
        3. Estimate gradients using numerical differentiation:
           For each parameter p:
             - Save original value
             - Set p = original + epsilon, compute loss_plus
             - Set p = original - epsilon, compute loss_minus
             - gradient = (loss_plus - loss_minus) / (2 * epsilon)
             - Restore original value
        4. Call optimizer.step(gradients)
        5. Accumulate loss for averaging

        Use epsilon = 1e-5 for numerical differentiation.

        Args:
            data: List of input feature vectors.
            labels: List of target values.

        Returns:
            Average loss over all data points.
        """
        # TODO: Implement (~25 lines)
        # Outer loop: iterate over data points
        #   Inner loop: iterate over model.parameters() to compute gradients
        #     Innermost loop: iterate over individual values in each parameter list
        raise NotImplementedError("Implement the training loop")

    def evaluate(
        self,
        data: list[list[float]],
        labels: list[float],
    ) -> dict:
        """Evaluate the model on data WITHOUT updating weights.

        Args:
            data: List of input feature vectors.
            labels: List of target values.

        Returns:
            Dict with 'mse', 'rmse', and 'mae'.
        """
        # TODO: Implement (~8 lines)
        # 1. Compute predictions for all data points
        # 2. Compute MSE using self.loss_fn.compute()
        # 3. Compute RMSE = sqrt(MSE)
        # 4. Compute MAE = mean(|pred - actual|)
        raise NotImplementedError("Implement evaluation")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def _verify():
    """Run basic checks to verify your implementation."""
    # Create a simple dataset: y = 2*x1 + 3*x2
    data = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]]
    labels = [2.0, 3.0, 5.0, 7.0]

    model = SimpleModel(input_dim=2, hidden_dim=4, seed=42)
    optimizer = SGDOptimizer(model.parameters(), lr=0.001)
    loss_fn = MSELoss()
    loop = TrainingLoop(model, optimizer, loss_fn)

    # Evaluate before training
    before = loop.evaluate(data, labels)
    print(f"Before training: MSE={before['mse']:.4f}, MAE={before['mae']:.4f}")

    # Train for a few epochs
    for epoch in range(5):
        loss = loop.train_one_epoch(data, labels)
        print(f"Epoch {epoch + 1}: avg_loss={loss:.4f}")

    # Evaluate after training
    after = loop.evaluate(data, labels)
    print(f"After training:  MSE={after['mse']:.4f}, MAE={after['mae']:.4f}")

    # Loss should decrease
    assert after["mse"] < before["mse"], "MSE should decrease after training"
    assert "rmse" in after, "evaluate() must return 'rmse'"
    assert "mae" in after, "evaluate() must return 'mae'"
    assert after["rmse"] == math.sqrt(after["mse"]), "RMSE should be sqrt(MSE)"

    print("[PASS] All verifications passed!")


if __name__ == "__main__":
    _verify()
