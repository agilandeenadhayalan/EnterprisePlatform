"""
Time Series Backtesting -- Proper validation that respects temporal ordering.

WHY THIS MATTERS:
Standard k-fold cross-validation randomly splits data, which BREAKS
temporal ordering. A model could be trained on future data and tested
on the past, creating an unrealistically optimistic evaluation.

Time series validation strategies maintain chronological order:
  - Walk-forward: train on expanding window, test on next chunk
  - Expanding window: same as walk-forward but explicit about growing training set
  - Sliding window: fixed-size training window that moves forward

For a mobility platform:
  - You can't use tomorrow's demand to predict today's
  - Walk-forward validation mimics real deployment: train on history, predict future
  - Helps catch issues like concept drift where older data hurts accuracy
"""


class WalkForwardValidator:
    """Walk-forward validation for time series.

    Creates n_splits train/test pairs where each test fold comes
    chronologically AFTER all training data. Training size grows
    with each split (expanding window).

    WHY WALK-FORWARD:
    This is the gold standard for time series evaluation because it
    exactly mimics how the model will be used in production: always
    trained on past data, always tested on future data.

    Example with n_splits=3, min_train=50, data_length=200:
      Split 1: train=[0..49],   test=[50..99]
      Split 2: train=[0..99],   test=[100..149]
      Split 3: train=[0..149],  test=[150..199]
    """

    def __init__(self, n_splits: int = 5, min_train_size: int = 50):
        if n_splits < 1:
            raise ValueError("n_splits must be >= 1")
        if min_train_size < 1:
            raise ValueError("min_train_size must be >= 1")
        self.n_splits = n_splits
        self.min_train_size = min_train_size

    def split(self, data: list) -> list[tuple[list, list]]:
        """Generate train/test index pairs for walk-forward validation.

        Args:
            data: The time series data (used only for length).

        Returns:
            List of (train_indices, test_indices) tuples.
        """
        n = len(data)
        if n < self.min_train_size + self.n_splits:
            raise ValueError(
                f"Data length ({n}) too short for {self.n_splits} splits "
                f"with min_train_size={self.min_train_size}"
            )

        # Calculate test size: divide remaining data after min_train among splits
        remaining = n - self.min_train_size
        test_size = remaining // self.n_splits

        if test_size < 1:
            raise ValueError("Not enough data for the requested number of splits")

        splits = []
        for i in range(self.n_splits):
            train_end = self.min_train_size + i * test_size
            test_start = train_end
            test_end = test_start + test_size

            # Last split takes all remaining data
            if i == self.n_splits - 1:
                test_end = n

            train_indices = list(range(train_end))
            test_indices = list(range(test_start, test_end))

            if test_indices:
                splits.append((train_indices, test_indices))

        return splits


class ExpandingWindowValidator:
    """Expanding window validation -- training window grows over time.

    Similar to walk-forward but with explicit control over initial
    training size and fixed test size.

    WHY EXPANDING:
    As more historical data becomes available, the model benefits from
    a larger training set. Expanding window captures this: each
    subsequent split trains on strictly more data than the previous.

    Example with initial_train=50, test_size=10, data_length=100:
      Split 1: train=[0..49],  test=[50..59]
      Split 2: train=[0..59],  test=[60..69]
      Split 3: train=[0..69],  test=[70..79]
      Split 4: train=[0..79],  test=[80..89]
      Split 5: train=[0..89],  test=[90..99]
    """

    def __init__(self, initial_train_size: int = 50, test_size: int = 10):
        if initial_train_size < 1:
            raise ValueError("initial_train_size must be >= 1")
        if test_size < 1:
            raise ValueError("test_size must be >= 1")
        self.initial_train_size = initial_train_size
        self.test_size = test_size

    def split(self, data: list) -> list[tuple[list, list]]:
        """Generate expanding window train/test splits.

        Returns:
            List of (train_indices, test_indices) tuples.
        """
        n = len(data)
        if n < self.initial_train_size + self.test_size:
            raise ValueError(
                f"Data length ({n}) too short for initial_train={self.initial_train_size} "
                f"+ test_size={self.test_size}"
            )

        splits = []
        train_end = self.initial_train_size

        while train_end + self.test_size <= n:
            train_indices = list(range(train_end))
            test_indices = list(range(train_end, train_end + self.test_size))
            splits.append((train_indices, test_indices))
            train_end += self.test_size

        return splits


class SlidingWindowValidator:
    """Sliding window validation -- fixed-size training window moves forward.

    Unlike expanding window, the training set has a FIXED size. Older
    data is dropped as the window slides forward.

    WHY SLIDING WINDOW:
    When data is non-stationary (common in real-world time series),
    very old data may hurt more than help. A sliding window focuses
    on recent patterns, which is often more representative of future
    behavior. Also useful when model training time scales with data size.

    Example with train_size=50, test_size=10, data_length=130:
      Split 1: train=[0..49],   test=[50..59]
      Split 2: train=[10..59],  test=[60..69]
      Split 3: train=[20..69],  test=[70..79]
      ...
    """

    def __init__(self, train_size: int = 50, test_size: int = 10):
        if train_size < 1:
            raise ValueError("train_size must be >= 1")
        if test_size < 1:
            raise ValueError("test_size must be >= 1")
        self.train_size = train_size
        self.test_size = test_size

    def split(self, data: list) -> list[tuple[list, list]]:
        """Generate sliding window train/test splits.

        Returns:
            List of (train_indices, test_indices) tuples.
        """
        n = len(data)
        if n < self.train_size + self.test_size:
            raise ValueError(
                f"Data length ({n}) too short for train_size={self.train_size} "
                f"+ test_size={self.test_size}"
            )

        splits = []
        start = 0

        while start + self.train_size + self.test_size <= n:
            train_indices = list(range(start, start + self.train_size))
            test_start = start + self.train_size
            test_indices = list(range(test_start, test_start + self.test_size))
            splits.append((train_indices, test_indices))
            start += self.test_size

        return splits
