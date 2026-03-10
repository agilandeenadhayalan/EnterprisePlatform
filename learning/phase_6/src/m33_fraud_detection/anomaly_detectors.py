"""
Anomaly Detection Algorithms — Z-score, Isolation Forest, LOF, and ensembles.

WHY THIS MATTERS:
Fraud detection starts with identifying transactions that look unusual.
These anomaly detectors operate on different principles:

  - Z-Score: how many standard deviations from the mean? Simple but
    effective for normally distributed data.
  - Isolation Forest: how easy is it to isolate a point via random splits?
    Anomalies are isolated quickly (short path length).
  - LOF (Local Outlier Factor): how dense is a point's neighborhood
    compared to its neighbors? Points in sparse regions are outliers.
  - Ensemble: combine multiple detectors for robustness. No single
    detector catches all types of fraud.

All implementations are pure Python — no sklearn required.
"""

import math
import random


class ZScoreDetector:
    """Z-score based anomaly detector.

    The z-score measures how many standard deviations a value is from
    the mean. Values with |z| > 3 are typically considered anomalous
    (only 0.3% of normally distributed data exceeds this threshold).
    """

    def __init__(self):
        self._mean: float = 0.0
        self._std: float = 0.0
        self._fitted = False

    def fit(self, data: list[float]) -> None:
        """Compute mean and standard deviation from training data."""
        if not data:
            raise ValueError("Cannot fit with empty data")
        n = len(data)
        self._mean = sum(data) / n
        variance = sum((x - self._mean) ** 2 for x in data) / n
        self._std = math.sqrt(variance)
        self._fitted = True

    def score(self, value: float) -> float:
        """Return the absolute z-score of a value.

        Higher scores indicate more anomalous values.
        """
        if not self._fitted:
            raise ValueError("Detector not fitted — call fit() first")
        if self._std == 0:
            return 0.0
        return abs((value - self._mean) / self._std)

    def is_anomaly(self, value: float, threshold: float = 3.0) -> bool:
        """Check if a value is anomalous based on its z-score."""
        return self.score(value) > threshold


class SimplifiedIsolationForest:
    """Isolation Forest anomaly detector using random binary splits.

    The key insight: anomalies are few and different, so they can be
    isolated from normal points with fewer random splits. The anomaly
    score is based on the average path length across multiple random
    trees — shorter paths mean more anomalous.

    This is a simplified pure-Python implementation. Production systems
    use scikit-learn's optimized version.
    """

    def __init__(self, n_trees: int = 10, max_depth: int = 8, seed: int = None):
        self._n_trees = n_trees
        self._max_depth = max_depth
        self._trees: list[dict] = []
        self._rng = random.Random(seed)
        self._fitted = False
        self._n_samples = 0

    def fit(self, data: list[list[float]], n_trees: int = None) -> None:
        """Build isolation trees from training data.

        Each tree recursively partitions the data with random splits
        (random feature, random threshold). The depth at which a point
        is isolated is its path length.
        """
        if not data:
            raise ValueError("Cannot fit with empty data")
        if n_trees is not None:
            self._n_trees = n_trees
        self._n_samples = len(data)
        self._trees = []
        for _ in range(self._n_trees):
            tree = self._build_tree(data, depth=0)
            self._trees.append(tree)
        self._fitted = True

    def _build_tree(self, data: list[list[float]], depth: int) -> dict:
        """Recursively build an isolation tree node."""
        if depth >= self._max_depth or len(data) <= 1:
            return {"type": "leaf", "size": len(data)}

        n_features = len(data[0])
        feat_idx = self._rng.randint(0, n_features - 1)
        feat_values = [row[feat_idx] for row in data]
        min_val, max_val = min(feat_values), max(feat_values)

        if min_val == max_val:
            return {"type": "leaf", "size": len(data)}

        threshold = self._rng.uniform(min_val, max_val)
        left = [row for row in data if row[feat_idx] < threshold]
        right = [row for row in data if row[feat_idx] >= threshold]

        if not left or not right:
            return {"type": "leaf", "size": len(data)}

        return {
            "type": "split",
            "feature": feat_idx,
            "threshold": threshold,
            "left": self._build_tree(left, depth + 1),
            "right": self._build_tree(right, depth + 1),
        }

    def _path_length(self, point: list[float], tree: dict, depth: int = 0) -> float:
        """Compute the path length for a point in a single tree."""
        if tree["type"] == "leaf":
            # Adjustment for unfinished splitting
            n = tree["size"]
            if n <= 1:
                return depth
            # Average path length in a BST (harmonic number approximation)
            return depth + self._c(n)
        if point[tree["feature"]] < tree["threshold"]:
            return self._path_length(point, tree["left"], depth + 1)
        return self._path_length(point, tree["right"], depth + 1)

    @staticmethod
    def _c(n: int) -> float:
        """Average path length of unsuccessful search in BST."""
        if n <= 1:
            return 0.0
        if n == 2:
            return 1.0
        h = math.log(n - 1) + 0.5772156649  # Euler-Mascheroni constant
        return 2.0 * h - 2.0 * (n - 1) / n

    def score(self, point: list[float]) -> float:
        """Return anomaly score for a point (0-1, higher = more anomalous).

        Score = 2^(-mean_path_length / c(n_samples))
        Normal points have score near 0.5; anomalies have score near 1.0.
        """
        if not self._fitted:
            raise ValueError("Detector not fitted — call fit() first")

        avg_path = sum(self._path_length(point, tree) for tree in self._trees) / len(self._trees)
        c_n = self._c(self._n_samples)
        if c_n == 0:
            return 0.5
        return 2.0 ** (-avg_path / c_n)

    def is_anomaly(self, point: list[float], threshold: float = 0.6) -> bool:
        """Check if a point is anomalous based on its isolation score."""
        return self.score(point) > threshold


class SimplifiedLOF:
    """Local Outlier Factor — density-based anomaly detection.

    LOF compares the density of a point's neighborhood to the density
    of its neighbors' neighborhoods. A point in a sparse region surrounded
    by dense regions has a high LOF score and is likely an outlier.

    This is simplified: we use Euclidean distance and a straightforward
    k-distance implementation.
    """

    def __init__(self, k: int = 5):
        self._k = k
        self._data: list[list[float]] = []
        self._fitted = False

    def fit(self, data: list[list[float]], k: int = None) -> None:
        """Store the training data for neighbor queries."""
        if not data:
            raise ValueError("Cannot fit with empty data")
        if k is not None:
            self._k = k
        self._data = [list(row) for row in data]
        self._k = min(self._k, len(self._data) - 1)
        if self._k < 1:
            self._k = 1
        self._fitted = True

    @staticmethod
    def _euclidean(a: list[float], b: list[float]) -> float:
        """Euclidean distance between two points."""
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))

    def _k_neighbors(self, point: list[float]) -> list[tuple[float, int]]:
        """Return the k nearest neighbors as (distance, index) pairs."""
        distances = [(self._euclidean(point, row), i) for i, row in enumerate(self._data)]
        distances.sort()
        # Skip distance=0 if the point is in the dataset
        result = []
        for d, i in distances:
            if len(result) >= self._k:
                break
            if d > 0 or self._data[i] != point:
                result.append((d, i))
            elif d == 0:
                # include it but keep looking — might be exact match
                result.append((d, i))
        return result[:self._k]

    def _k_distance(self, point: list[float]) -> float:
        """Distance to the k-th nearest neighbor."""
        if not self._fitted:
            raise ValueError("Detector not fitted — call fit() first")
        neighbors = self._k_neighbors(point)
        if not neighbors:
            return 0.0
        return neighbors[-1][0]

    def score(self, point: list[float]) -> float:
        """LOF score: ratio of point's k-distance to avg k-distance of neighbors.

        Score > 1 indicates the point is in a sparser region than its
        neighbors (potential outlier). Score near 1 means similar density.
        """
        if not self._fitted:
            raise ValueError("Detector not fitted — call fit() first")

        neighbors = self._k_neighbors(point)
        if not neighbors:
            return 1.0

        point_kd = self._k_distance(point)
        if point_kd == 0:
            # Point is very close to its neighbors, low anomaly
            return 0.5

        neighbor_kds = []
        for _, idx in neighbors:
            nkd = self._k_distance(self._data[idx])
            neighbor_kds.append(nkd)

        avg_neighbor_kd = sum(neighbor_kds) / len(neighbor_kds) if neighbor_kds else 1.0
        if avg_neighbor_kd == 0:
            return 1.0

        return point_kd / avg_neighbor_kd

    def is_anomaly(self, point: list[float], threshold: float = 1.5) -> bool:
        """Check if a point is anomalous based on its LOF score."""
        return self.score(point) > threshold


class EnsembleDetector:
    """Weighted ensemble of multiple anomaly detectors.

    Combines scores from multiple detectors using weighted averaging.
    The is_anomaly decision uses majority voting among the individual
    detectors' is_anomaly results.
    """

    def __init__(self):
        self._detectors: list[tuple] = []  # (detector, weight)

    def add_detector(self, detector, weight: float = 1.0) -> None:
        """Add a detector with a weight to the ensemble."""
        self._detectors.append((detector, weight))

    def score(self, value_or_point) -> float:
        """Weighted average of detector scores.

        Handles both scalar values (for ZScoreDetector) and vector points
        (for IsolationForest and LOF) transparently.
        """
        if not self._detectors:
            raise ValueError("No detectors in ensemble")

        total_weight = sum(w for _, w in self._detectors)
        if total_weight == 0:
            return 0.0

        weighted_sum = 0.0
        for detector, weight in self._detectors:
            s = detector.score(value_or_point)
            weighted_sum += s * weight

        return weighted_sum / total_weight

    def is_anomaly(self, value_or_point) -> bool:
        """Majority vote among detectors.

        If more than half the detectors (weighted) flag the point as
        anomalous, the ensemble flags it too.
        """
        if not self._detectors:
            raise ValueError("No detectors in ensemble")

        anomaly_weight = 0.0
        total_weight = sum(w for _, w in self._detectors)

        for detector, weight in self._detectors:
            if detector.is_anomaly(value_or_point):
                anomaly_weight += weight

        return anomaly_weight > total_weight / 2
