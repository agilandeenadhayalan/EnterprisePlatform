"""
Matrix Factorization -- Latent factor models for recommendations.

WHY THIS MATTERS:
The user-item interaction matrix is typically very sparse (users rate <1%
of items). Matrix factorization discovers latent factors that explain
observed ratings. For example, a "genre preference" factor might emerge
where action-movie-lovers cluster together.

ALS (Alternating Least Squares) is preferred for implicit feedback data
and parallelizes well for large-scale systems.

Math:
  R ~ U x V^T
  where R is (n_users x n_items), U is (n_users x k), V is (n_items x k)
  k = number of latent factors (typically 5-100)
"""

import math
import random


class ALSMatrixFactorization:
    """Alternating Least Squares for matrix factorization.

    Decomposes user-item matrix R into U x V^T where:
      U = user latent factor matrix (n_users x n_factors)
      V = item latent factor matrix (n_items x n_factors)

    Alternates between:
      1. Fix V, solve for U row-by-row (each user's factors)
      2. Fix U, solve for V row-by-row (each item's factors)

    Each sub-problem is a regularized least-squares:
      u_i = (V_I^T V_I + lambda*I)^{-1} V_I^T r_i
    where V_I is the subset of V for items user i has rated.

    WHY ALS:
    Unlike gradient descent, ALS solves each step exactly (closed-form),
    converging more reliably. It naturally handles the sparsity of real
    recommendation data and parallelizes across users/items.
    """

    def __init__(
        self,
        n_factors: int = 5,
        n_iterations: int = 20,
        regularization: float = 0.1,
        seed: int = 42,
    ):
        self.n_factors = n_factors
        self.n_iterations = n_iterations
        self.regularization = regularization
        self.seed = seed
        self._U: list[list[float]] = []
        self._V: list[list[float]] = []
        self._user_ids: list[str] = []
        self._item_ids: list[str] = []
        self._user_index: dict[str, int] = {}
        self._item_index: dict[str, int] = {}
        self._R: list[list[float]] = []

    def fit(
        self,
        user_item_matrix: list[list[float]],
        user_ids: list[str],
        item_ids: list[str],
    ) -> None:
        """Fit the ALS model to the user-item matrix.

        Args:
            user_item_matrix: Rows = users, cols = items. 0 = unobserved.
            user_ids: User identifiers.
            item_ids: Item identifiers.
        """
        self._R = [row[:] for row in user_item_matrix]
        self._user_ids = list(user_ids)
        self._item_ids = list(item_ids)
        self._user_index = {uid: i for i, uid in enumerate(user_ids)}
        self._item_index = {iid: i for i, iid in enumerate(item_ids)}

        n_users = len(user_ids)
        n_items = len(item_ids)
        rng = random.Random(self.seed)

        # Initialize U and V with small random values
        self._U = [
            [rng.gauss(0, 0.1) for _ in range(self.n_factors)]
            for _ in range(n_users)
        ]
        self._V = [
            [rng.gauss(0, 0.1) for _ in range(self.n_factors)]
            for _ in range(n_items)
        ]

        # Alternating optimization
        for iteration in range(self.n_iterations):
            # Step 1: Fix V, update U
            for i in range(n_users):
                self._update_user(i)

            # Step 2: Fix U, update V
            for j in range(n_items):
                self._update_item(j)

    def _update_user(self, user_idx: int) -> None:
        """Update user factors with V fixed.

        Solves: u_i = (V_I^T V_I + lambda*I)^{-1} V_I^T r_i
        Simplified: for each factor k, update independently using
        gradient-like steps from observed ratings.
        """
        n_items = len(self._item_ids)
        rated_items = []
        for j in range(n_items):
            if self._R[user_idx][j] != 0:
                rated_items.append(j)

        if not rated_items:
            return

        # Build A = V_I^T V_I + lambda*I and b = V_I^T r_i
        k = self.n_factors
        A = [[0.0] * k for _ in range(k)]
        b = [0.0] * k

        for j in rated_items:
            v_j = self._V[j]
            r_ij = self._R[user_idx][j]
            for f1 in range(k):
                b[f1] += v_j[f1] * r_ij
                for f2 in range(k):
                    A[f1][f2] += v_j[f1] * v_j[f2]

        # Add regularization
        for f in range(k):
            A[f][f] += self.regularization

        # Solve A * u = b using simple Gaussian elimination
        solution = self._solve_linear(A, b)
        self._U[user_idx] = solution

    def _update_item(self, item_idx: int) -> None:
        """Update item factors with U fixed."""
        n_users = len(self._user_ids)
        rating_users = []
        for i in range(n_users):
            if self._R[i][item_idx] != 0:
                rating_users.append(i)

        if not rating_users:
            return

        k = self.n_factors
        A = [[0.0] * k for _ in range(k)]
        b = [0.0] * k

        for i in rating_users:
            u_i = self._U[i]
            r_ij = self._R[i][item_idx]
            for f1 in range(k):
                b[f1] += u_i[f1] * r_ij
                for f2 in range(k):
                    A[f1][f2] += u_i[f1] * u_i[f2]

        for f in range(k):
            A[f][f] += self.regularization

        solution = self._solve_linear(A, b)
        self._V[item_idx] = solution

    def _solve_linear(self, A: list[list[float]], b: list[float]) -> list[float]:
        """Solve Ax = b using Gaussian elimination with partial pivoting."""
        n = len(b)
        # Augmented matrix
        aug = [A[i][:] + [b[i]] for i in range(n)]

        # Forward elimination
        for col in range(n):
            # Partial pivoting
            max_row = col
            max_val = abs(aug[col][col])
            for row in range(col + 1, n):
                if abs(aug[row][col]) > max_val:
                    max_val = abs(aug[row][col])
                    max_row = row
            aug[col], aug[max_row] = aug[max_row], aug[col]

            if abs(aug[col][col]) < 1e-12:
                continue

            for row in range(col + 1, n):
                factor = aug[row][col] / aug[col][col]
                for j in range(col, n + 1):
                    aug[row][j] -= factor * aug[col][j]

        # Back substitution
        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            if abs(aug[i][i]) < 1e-12:
                x[i] = 0.0
                continue
            x[i] = aug[i][n]
            for j in range(i + 1, n):
                x[i] -= aug[i][j] * x[j]
            x[i] /= aug[i][i]

        return x

    def predict(self, user_id: str, item_id: str) -> float:
        """Predict rating for a user-item pair.

        prediction = U[user] . V[item] (dot product of latent factors)
        """
        if user_id not in self._user_index or item_id not in self._item_index:
            return 0.0

        u = self._U[self._user_index[user_id]]
        v = self._V[self._item_index[item_id]]
        return sum(ui * vi for ui, vi in zip(u, v))

    def recommend(self, user_id: str, n: int = 5) -> list[tuple[str, float]]:
        """Recommend top-n items for a user.

        Predicts ratings for all unrated items and returns the highest.
        """
        if user_id not in self._user_index:
            return []

        user_idx = self._user_index[user_id]
        predictions = []

        for j, item_id in enumerate(self._item_ids):
            if self._R[user_idx][j] != 0:
                continue  # skip already-rated items
            score = self.predict(user_id, item_id)
            predictions.append((item_id, score))

        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:n]

    def reconstruction_error(self) -> float:
        """Compute RMSE between R and U*V^T for observed entries.

        Only counts entries where R != 0 (observed ratings), since
        unobserved entries are not necessarily zero-rated.
        """
        total_error = 0.0
        count = 0

        for i in range(len(self._user_ids)):
            for j in range(len(self._item_ids)):
                if self._R[i][j] != 0:
                    predicted = sum(
                        self._U[i][f] * self._V[j][f]
                        for f in range(self.n_factors)
                    )
                    error = self._R[i][j] - predicted
                    total_error += error * error
                    count += 1

        if count == 0:
            return 0.0

        return math.sqrt(total_error / count)
