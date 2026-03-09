"""
Teaching-oriented data preprocessing utilities.

Provides pure-Python implementations of common preprocessing
transformations used in ML pipelines.  Each class follows the
familiar ``fit`` / ``transform`` / ``fit_transform`` pattern
so learners can understand the mechanics before moving to
production libraries like scikit-learn.

Scalers
-------
- :class:`StandardScaler`  Z-score normalisation (mean=0, std=1).
- :class:`MinMaxScaler`    Scales features to [0, 1].

Encoders
--------
- :class:`CategoryEncoder`  Integer and one-hot encoding for
  categorical features.

No external dependencies are required — all implementations use
only the ``math`` standard-library module.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "StandardScaler",
    "MinMaxScaler",
    "CategoryEncoder",
]


class StandardScaler:
    """Z-score standardisation: transforms data to mean=0, std=1.

    This is one of the most common preprocessing steps in ML pipelines.
    The scaler learns the mean and standard deviation from a training
    set and then applies the same transformation to new data.

    Examples
    --------
    >>> scaler = StandardScaler()
    >>> data = [10.0, 20.0, 30.0, 40.0, 50.0]
    >>> scaled = scaler.fit_transform(data)
    >>> # scaled values will have mean ~ 0 and std ~ 1
    >>> original = scaler.inverse_transform(scaled)
    >>> # original ≈ data (within floating-point precision)
    """

    def __init__(self) -> None:
        self._mean: Optional[float] = None
        self._std: Optional[float] = None
        self._fitted = False

    @property
    def mean(self) -> Optional[float]:
        """The mean learned during fitting."""
        return self._mean

    @property
    def std(self) -> Optional[float]:
        """The standard deviation learned during fitting."""
        return self._std

    def fit(self, data: List[float]) -> "StandardScaler":
        """Learn the mean and standard deviation from the data.

        Parameters
        ----------
        data : list[float]
            Training data to compute statistics from.

        Returns
        -------
        StandardScaler
            Returns ``self`` for method chaining.

        Raises
        ------
        ValueError
            If *data* is empty.
        """
        if not data:
            raise ValueError("Cannot fit on empty data")

        n = len(data)
        self._mean = sum(data) / n

        variance = sum((x - self._mean) ** 2 for x in data) / n
        self._std = math.sqrt(variance) if variance > 0 else 1.0

        self._fitted = True
        logger.debug(
            "StandardScaler fit: mean=%.6f, std=%.6f (n=%d)",
            self._mean,
            self._std,
            n,
        )
        return self

    def transform(self, data: List[float]) -> List[float]:
        """Apply the learned transformation to new data.

        Parameters
        ----------
        data : list[float]
            Data to transform.

        Returns
        -------
        list[float]
            Standardised values.

        Raises
        ------
        RuntimeError
            If the scaler has not been fitted yet.
        """
        self._check_fitted()
        result = [(x - self._mean) / self._std for x in data]
        logger.debug("StandardScaler transformed %d values", len(data))
        return result

    def fit_transform(self, data: List[float]) -> List[float]:
        """Fit and transform in one step.

        Parameters
        ----------
        data : list[float]
            Training data.

        Returns
        -------
        list[float]
            Standardised values.
        """
        return self.fit(data).transform(data)

    def inverse_transform(self, data: List[float]) -> List[float]:
        """Reverse the standardisation to recover original scale.

        Parameters
        ----------
        data : list[float]
            Standardised values.

        Returns
        -------
        list[float]
            Values in the original scale.

        Raises
        ------
        RuntimeError
            If the scaler has not been fitted yet.
        """
        self._check_fitted()
        result = [(x * self._std) + self._mean for x in data]
        logger.debug("StandardScaler inverse-transformed %d values", len(data))
        return result

    def _check_fitted(self) -> None:
        """Raise if the scaler has not been fitted."""
        if not self._fitted:
            raise RuntimeError(
                "StandardScaler has not been fitted yet. Call fit() first."
            )


class MinMaxScaler:
    """Min-max normalisation: scales data to [0, 1].

    Maps the minimum observed value to 0 and the maximum to 1.
    Useful when features have different ranges and you want them
    on a comparable scale without assuming a Gaussian distribution.

    Examples
    --------
    >>> scaler = MinMaxScaler()
    >>> data = [100.0, 200.0, 300.0]
    >>> scaled = scaler.fit_transform(data)
    >>> # scaled == [0.0, 0.5, 1.0]
    """

    def __init__(self) -> None:
        self._min: Optional[float] = None
        self._max: Optional[float] = None
        self._range: Optional[float] = None
        self._fitted = False

    @property
    def data_min(self) -> Optional[float]:
        """The minimum value learned during fitting."""
        return self._min

    @property
    def data_max(self) -> Optional[float]:
        """The maximum value learned during fitting."""
        return self._max

    def fit(self, data: List[float]) -> "MinMaxScaler":
        """Learn the min and max from the data.

        Parameters
        ----------
        data : list[float]
            Training data.

        Returns
        -------
        MinMaxScaler
            Returns ``self`` for method chaining.

        Raises
        ------
        ValueError
            If *data* is empty.
        """
        if not data:
            raise ValueError("Cannot fit on empty data")

        self._min = min(data)
        self._max = max(data)
        self._range = self._max - self._min if self._max != self._min else 1.0
        self._fitted = True

        logger.debug(
            "MinMaxScaler fit: min=%.6f, max=%.6f (n=%d)",
            self._min,
            self._max,
            len(data),
        )
        return self

    def transform(self, data: List[float]) -> List[float]:
        """Apply the learned transformation to new data.

        Parameters
        ----------
        data : list[float]
            Data to transform.

        Returns
        -------
        list[float]
            Scaled values in [0, 1] (may exceed bounds for unseen values).

        Raises
        ------
        RuntimeError
            If the scaler has not been fitted yet.
        """
        self._check_fitted()
        result = [(x - self._min) / self._range for x in data]
        logger.debug("MinMaxScaler transformed %d values", len(data))
        return result

    def fit_transform(self, data: List[float]) -> List[float]:
        """Fit and transform in one step.

        Parameters
        ----------
        data : list[float]
            Training data.

        Returns
        -------
        list[float]
            Scaled values.
        """
        return self.fit(data).transform(data)

    def inverse_transform(self, data: List[float]) -> List[float]:
        """Reverse the scaling to recover original values.

        Parameters
        ----------
        data : list[float]
            Scaled values.

        Returns
        -------
        list[float]
            Values in the original scale.

        Raises
        ------
        RuntimeError
            If the scaler has not been fitted yet.
        """
        self._check_fitted()
        result = [(x * self._range) + self._min for x in data]
        logger.debug("MinMaxScaler inverse-transformed %d values", len(data))
        return result

    def _check_fitted(self) -> None:
        """Raise if the scaler has not been fitted."""
        if not self._fitted:
            raise RuntimeError(
                "MinMaxScaler has not been fitted yet. Call fit() first."
            )


class CategoryEncoder:
    """Integer and one-hot encoding for categorical features.

    Maps string categories to integer indices and provides one-hot
    vector representations.  Useful for converting categorical columns
    into numeric form for ML models.

    Examples
    --------
    >>> enc = CategoryEncoder()
    >>> enc.fit(["red", "green", "blue"])
    >>> enc.encode("green")
    1
    >>> enc.one_hot("green")
    [0, 1, 0]
    >>> enc.decode(2)
    'blue'
    """

    def __init__(self) -> None:
        self._categories: List[Any] = []
        self._cat_to_idx: Dict[Any, int] = {}
        self._fitted = False

    @property
    def categories(self) -> List[Any]:
        """The list of known categories (in index order)."""
        return list(self._categories)

    @property
    def num_categories(self) -> int:
        """Number of known categories."""
        return len(self._categories)

    def fit(self, categories: List[Any]) -> "CategoryEncoder":
        """Learn the set of categories.

        Parameters
        ----------
        categories : list
            Unique category values.  Duplicates are removed and the
            order is preserved (first occurrence wins).

        Returns
        -------
        CategoryEncoder
            Returns ``self`` for method chaining.

        Raises
        ------
        ValueError
            If *categories* is empty.
        """
        if not categories:
            raise ValueError("Cannot fit on empty category list")

        # Deduplicate while preserving order
        seen: set = set()
        unique: List[Any] = []
        for cat in categories:
            if cat not in seen:
                seen.add(cat)
                unique.append(cat)

        self._categories = unique
        self._cat_to_idx = {cat: idx for idx, cat in enumerate(unique)}
        self._fitted = True

        logger.debug(
            "CategoryEncoder fit: %d categories", len(self._categories)
        )
        return self

    def encode(self, value: Any) -> int:
        """Encode a category as an integer index.

        Parameters
        ----------
        value : any
            Category value.

        Returns
        -------
        int
            Zero-based index.

        Raises
        ------
        RuntimeError
            If the encoder has not been fitted.
        KeyError
            If *value* was not seen during fitting.
        """
        self._check_fitted()
        if value not in self._cat_to_idx:
            raise KeyError(
                f"Unknown category '{value}'. "
                f"Known categories: {self._categories}"
            )
        return self._cat_to_idx[value]

    def decode(self, index: int) -> Any:
        """Decode an integer index back to its category.

        Parameters
        ----------
        index : int
            Zero-based index.

        Returns
        -------
        any
            The original category value.

        Raises
        ------
        RuntimeError
            If the encoder has not been fitted.
        IndexError
            If *index* is out of range.
        """
        self._check_fitted()
        if index < 0 or index >= len(self._categories):
            raise IndexError(
                f"Index {index} out of range for {len(self._categories)} categories"
            )
        return self._categories[index]

    def one_hot(self, value: Any) -> List[int]:
        """Encode a category as a one-hot vector.

        Parameters
        ----------
        value : any
            Category value.

        Returns
        -------
        list[int]
            Binary vector of length ``num_categories`` with a single 1
            at the position of the encoded category.

        Raises
        ------
        RuntimeError
            If the encoder has not been fitted.
        KeyError
            If *value* was not seen during fitting.
        """
        self._check_fitted()
        idx = self.encode(value)
        vec = [0] * len(self._categories)
        vec[idx] = 1
        logger.debug("One-hot encoded '%s' -> index %d", value, idx)
        return vec

    def _check_fitted(self) -> None:
        """Raise if the encoder has not been fitted."""
        if not self._fitted:
            raise RuntimeError(
                "CategoryEncoder has not been fitted yet. Call fit() first."
            )
