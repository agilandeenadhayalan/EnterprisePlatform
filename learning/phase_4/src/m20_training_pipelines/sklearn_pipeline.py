"""
Sklearn-Style Pipeline and Cross-Validation
=============================================

In production ML, data flows through a series of transformations before
reaching the model. A **Pipeline** chains these steps together so that
the entire preprocessing + prediction flow is reproducible and testable.

**Cross-Validation** evaluates how well a pipeline generalizes by
training and testing on multiple different splits of the data. This
prevents overfitting to a single train/test split and gives a more
reliable estimate of real-world performance.

Key concepts:
- Pipeline ensures that all preprocessing is applied consistently
  during both training and inference (a common source of bugs).
- K-fold CV splits data into K parts, trains on K-1, tests on 1,
  rotating through all K possibilities.
- The mean and std of scores across folds tells you both expected
  performance and how stable the model is.
"""

from __future__ import annotations

import random
from copy import deepcopy


class Pipeline:
    """Teaching implementation of sklearn-style pipeline.

    A pipeline chains together multiple processing steps, where each step
    is a (name, transformer_or_model) tuple. All steps except the last
    must implement fit(X, y) and transform(X). The last step must
    implement fit(X, y) and predict(X).

    Example:
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("model", LinearRegression()),
        ])
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)
    """

    def __init__(self, steps: list[tuple[str, object]]) -> None:
        """Initialize the pipeline.

        Args:
            steps: List of (name, estimator) tuples. Names must be unique.

        Raises:
            ValueError: If steps is empty or names are not unique.
        """
        if not steps:
            raise ValueError("Pipeline must have at least one step")

        names = [name for name, _ in steps]
        if len(names) != len(set(names)):
            raise ValueError("Step names must be unique")

        self.steps = steps
        self._fitted = False

    def fit(self, X: list, y: list) -> "Pipeline":
        """Fit all steps in sequence.

        For each step except the last:
            1. Call step.fit(X, y)
            2. Transform X using step.transform(X)
            3. Pass transformed X to the next step.

        The last step is just fitted (not transformed).

        Returns:
            self (for method chaining).
        """
        X_transformed = X
        for i, (name, step) in enumerate(self.steps):
            if i < len(self.steps) - 1:
                # Intermediate step: fit and transform
                step.fit(X_transformed, y)
                X_transformed = step.transform(X_transformed)
            else:
                # Final step: just fit
                step.fit(X_transformed, y)

        self._fitted = True
        return self

    def predict(self, X: list) -> list:
        """Run input through all transforms, then predict with final step.

        Raises:
            RuntimeError: If the pipeline hasn't been fitted.
        """
        if not self._fitted:
            raise RuntimeError("Pipeline must be fitted before predict()")

        X_transformed = X
        for i, (name, step) in enumerate(self.steps):
            if i < len(self.steps) - 1:
                X_transformed = step.transform(X_transformed)
            else:
                return step.predict(X_transformed)

        return []  # pragma: no cover

    def fit_predict(self, X: list, y: list) -> list:
        """Convenience: fit the pipeline and return predictions on the same data."""
        self.fit(X, y)
        return self.predict(X)

    def get_params(self) -> dict:
        """Return a dict of all step names and their parameters."""
        params = {}
        for name, step in self.steps:
            if hasattr(step, "get_params"):
                step_params = step.get_params()
            else:
                step_params = {
                    k: v for k, v in step.__dict__.items()
                    if not k.startswith("_")
                }
            params[name] = step_params
        return params


class CrossValidator:
    """K-fold cross-validation.

    Splits data into K folds, trains on K-1 folds, evaluates on the
    remaining fold, and rotates through all K possibilities.

    This gives a more reliable performance estimate than a single
    train/test split because:
    1. Every data point is used for both training and validation.
    2. The variance across folds indicates model stability.
    3. Outlier splits are averaged out.
    """

    def __init__(
        self,
        n_folds: int = 5,
        shuffle: bool = True,
        seed: int = 42,
    ) -> None:
        if n_folds < 2:
            raise ValueError("n_folds must be >= 2")
        self.n_folds = n_folds
        self.shuffle = shuffle
        self.seed = seed

    def split(self, data: list) -> list[tuple[list[int], list[int]]]:
        """Generate train/validation index splits.

        Args:
            data: The dataset (only its length matters).

        Returns:
            List of (train_indices, val_indices) tuples, one per fold.
        """
        n = len(data)
        indices = list(range(n))

        if self.shuffle:
            rng = random.Random(self.seed)
            rng.shuffle(indices)

        # Divide indices into n_folds approximately equal parts
        fold_sizes = [n // self.n_folds] * self.n_folds
        for i in range(n % self.n_folds):
            fold_sizes[i] += 1

        folds = []
        start = 0
        for size in fold_sizes:
            folds.append(indices[start: start + size])
            start += size

        # Generate train/val splits
        splits = []
        for fold_idx in range(self.n_folds):
            val_indices = folds[fold_idx]
            train_indices = []
            for i, fold in enumerate(folds):
                if i != fold_idx:
                    train_indices.extend(fold)
            splits.append((sorted(train_indices), sorted(val_indices)))

        return splits

    def cross_validate(
        self,
        pipeline: Pipeline,
        X: list,
        y: list,
        metric_fn,
    ) -> dict:
        """Run cross-validation and return scores.

        Args:
            pipeline: The pipeline to evaluate (will be deep-copied per fold).
            X: Input features.
            y: Target values.
            metric_fn: Function(y_true, y_pred) -> float score.

        Returns:
            Dict with 'fold_scores', 'mean', and 'std'.
        """
        splits = self.split(X)
        fold_scores = []

        for train_idx, val_idx in splits:
            # Extract train/val data
            X_train = [X[i] for i in train_idx]
            y_train = [y[i] for i in train_idx]
            X_val = [X[i] for i in val_idx]
            y_val = [y[i] for i in val_idx]

            # Deep copy to avoid state leaking between folds
            fold_pipeline = deepcopy(pipeline)
            fold_pipeline.fit(X_train, y_train)
            predictions = fold_pipeline.predict(X_val)

            score = metric_fn(y_val, predictions)
            fold_scores.append(score)

        mean_score = sum(fold_scores) / len(fold_scores)
        variance = sum((s - mean_score) ** 2 for s in fold_scores) / len(fold_scores)
        std_score = variance ** 0.5

        return {
            "fold_scores": fold_scores,
            "mean": mean_score,
            "std": std_score,
        }
