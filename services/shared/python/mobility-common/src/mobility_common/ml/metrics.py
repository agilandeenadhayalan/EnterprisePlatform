"""
Pure-Python ML evaluation metrics.

Provides common regression and classification metrics without any
external dependencies (uses only the ``math`` standard-library module).
This keeps the shared library lightweight while giving every service
consistent metric calculations.

Regression metrics
------------------
- :func:`rmse`  Root Mean Squared Error
- :func:`mae`   Mean Absolute Error
- :func:`mape`  Mean Absolute Percentage Error
- :func:`r_squared`  Coefficient of determination (R^2)

Classification metrics
----------------------
- :func:`accuracy`   Overall accuracy
- :func:`precision`  Precision (positive predictive value)
- :func:`recall`     Recall (sensitivity / true positive rate)
- :func:`f1_score`   Harmonic mean of precision and recall
- :func:`confusion_matrix`  Counts of TP, FP, TN, FN
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "rmse",
    "mae",
    "mape",
    "r_squared",
    "accuracy",
    "precision",
    "recall",
    "f1_score",
    "confusion_matrix",
]


# ── Regression Metrics ──


def rmse(actual: List[float], predicted: List[float]) -> float:
    """Root Mean Squared Error.

    Parameters
    ----------
    actual : list[float]
        Ground-truth values.
    predicted : list[float]
        Model predictions.

    Returns
    -------
    float
        RMSE value (lower is better).

    Raises
    ------
    ValueError
        If the lists are empty or differ in length.
    """
    _validate_lengths(actual, predicted)
    n = len(actual)
    mse = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / n
    result = math.sqrt(mse)
    logger.debug("RMSE = %.6f (n=%d)", result, n)
    return result


def mae(actual: List[float], predicted: List[float]) -> float:
    """Mean Absolute Error.

    Parameters
    ----------
    actual : list[float]
        Ground-truth values.
    predicted : list[float]
        Model predictions.

    Returns
    -------
    float
        MAE value (lower is better).

    Raises
    ------
    ValueError
        If the lists are empty or differ in length.
    """
    _validate_lengths(actual, predicted)
    n = len(actual)
    result = sum(abs(a - p) for a, p in zip(actual, predicted)) / n
    logger.debug("MAE = %.6f (n=%d)", result, n)
    return result


def mape(actual: List[float], predicted: List[float]) -> float:
    """Mean Absolute Percentage Error.

    Handles zero actual values gracefully by skipping them in the
    calculation.  If all actual values are zero, returns ``float('inf')``.

    Parameters
    ----------
    actual : list[float]
        Ground-truth values.
    predicted : list[float]
        Model predictions.

    Returns
    -------
    float
        MAPE as a decimal (e.g. 0.05 = 5%).  Returns ``float('inf')``
        if all actual values are zero.

    Raises
    ------
    ValueError
        If the lists are empty or differ in length.
    """
    _validate_lengths(actual, predicted)
    total = 0.0
    count = 0
    for a, p in zip(actual, predicted):
        if a == 0:
            logger.debug("MAPE: skipping zero actual value")
            continue
        total += abs((a - p) / a)
        count += 1

    if count == 0:
        logger.warning("MAPE: all actual values are zero — returning inf")
        return float("inf")

    result = total / count
    logger.debug("MAPE = %.6f (n=%d, used=%d)", result, len(actual), count)
    return result


def r_squared(actual: List[float], predicted: List[float]) -> float:
    """Coefficient of determination (R-squared).

    Measures how well predictions explain the variance in actual values.

    Parameters
    ----------
    actual : list[float]
        Ground-truth values.
    predicted : list[float]
        Model predictions.

    Returns
    -------
    float
        R^2 value.  1.0 = perfect fit, 0.0 = predicting the mean,
        negative = worse than the mean.

    Raises
    ------
    ValueError
        If the lists are empty or differ in length.
    """
    _validate_lengths(actual, predicted)
    n = len(actual)
    mean_actual = sum(actual) / n

    ss_res = sum((a - p) ** 2 for a, p in zip(actual, predicted))
    ss_tot = sum((a - mean_actual) ** 2 for a in actual)

    if ss_tot == 0:
        logger.warning("R-squared: all actual values are identical — returning 0.0")
        return 0.0

    result = 1.0 - (ss_res / ss_tot)
    logger.debug("R-squared = %.6f (n=%d)", result, n)
    return result


# ── Classification Metrics ──


def accuracy(actual: List[Any], predicted: List[Any]) -> float:
    """Overall classification accuracy.

    Parameters
    ----------
    actual : list
        Ground-truth labels.
    predicted : list
        Predicted labels.

    Returns
    -------
    float
        Fraction of correct predictions in [0, 1].

    Raises
    ------
    ValueError
        If the lists are empty or differ in length.
    """
    _validate_lengths(actual, predicted)
    n = len(actual)
    correct = sum(1 for a, p in zip(actual, predicted) if a == p)
    result = correct / n
    logger.debug("Accuracy = %.6f (%d/%d)", result, correct, n)
    return result


def precision(
    actual: List[Any],
    predicted: List[Any],
    positive_label: Any = 1,
) -> float:
    """Precision (positive predictive value).

    Parameters
    ----------
    actual : list
        Ground-truth labels.
    predicted : list
        Predicted labels.
    positive_label : any
        The label considered as "positive" (default ``1``).

    Returns
    -------
    float
        Precision in [0, 1].  Returns 0.0 if no positive predictions.

    Raises
    ------
    ValueError
        If the lists are empty or differ in length.
    """
    _validate_lengths(actual, predicted)
    cm = confusion_matrix(actual, predicted, positive_label=positive_label)
    tp = cm["tp"]
    fp = cm["fp"]
    if tp + fp == 0:
        logger.warning("Precision: no positive predictions — returning 0.0")
        return 0.0
    result = tp / (tp + fp)
    logger.debug("Precision = %.6f (tp=%d, fp=%d)", result, tp, fp)
    return result


def recall(
    actual: List[Any],
    predicted: List[Any],
    positive_label: Any = 1,
) -> float:
    """Recall (sensitivity / true positive rate).

    Parameters
    ----------
    actual : list
        Ground-truth labels.
    predicted : list
        Predicted labels.
    positive_label : any
        The label considered as "positive" (default ``1``).

    Returns
    -------
    float
        Recall in [0, 1].  Returns 0.0 if no actual positives.

    Raises
    ------
    ValueError
        If the lists are empty or differ in length.
    """
    _validate_lengths(actual, predicted)
    cm = confusion_matrix(actual, predicted, positive_label=positive_label)
    tp = cm["tp"]
    fn = cm["fn"]
    if tp + fn == 0:
        logger.warning("Recall: no actual positives — returning 0.0")
        return 0.0
    result = tp / (tp + fn)
    logger.debug("Recall = %.6f (tp=%d, fn=%d)", result, tp, fn)
    return result


def f1_score(
    actual: List[Any],
    predicted: List[Any],
    positive_label: Any = 1,
) -> float:
    """F1 score (harmonic mean of precision and recall).

    Parameters
    ----------
    actual : list
        Ground-truth labels.
    predicted : list
        Predicted labels.
    positive_label : any
        The label considered as "positive" (default ``1``).

    Returns
    -------
    float
        F1 in [0, 1].  Returns 0.0 if precision + recall = 0.

    Raises
    ------
    ValueError
        If the lists are empty or differ in length.
    """
    _validate_lengths(actual, predicted)
    p = precision(actual, predicted, positive_label=positive_label)
    r = recall(actual, predicted, positive_label=positive_label)
    if p + r == 0:
        logger.warning("F1: precision + recall = 0 — returning 0.0")
        return 0.0
    result = 2.0 * (p * r) / (p + r)
    logger.debug("F1 = %.6f (precision=%.4f, recall=%.4f)", result, p, r)
    return result


def confusion_matrix(
    actual: List[Any],
    predicted: List[Any],
    labels: Optional[List[Any]] = None,
    positive_label: Any = 1,
) -> Dict[str, int]:
    """Compute a binary confusion matrix.

    Parameters
    ----------
    actual : list
        Ground-truth labels.
    predicted : list
        Predicted labels.
    labels : list or None
        If provided, only these labels are considered.  Otherwise, all
        unique labels from *actual* and *predicted* are used.
    positive_label : any
        The label treated as "positive" for TP/FP/TN/FN counting
        (default ``1``).

    Returns
    -------
    dict
        ``{"tp": int, "fp": int, "tn": int, "fn": int}``.

    Raises
    ------
    ValueError
        If the lists are empty or differ in length.
    """
    _validate_lengths(actual, predicted)

    tp = fp = tn = fn = 0
    for a, p in zip(actual, predicted):
        if labels is not None and a not in labels and p not in labels:
            continue
        if p == positive_label:
            if a == positive_label:
                tp += 1
            else:
                fp += 1
        else:
            if a == positive_label:
                fn += 1
            else:
                tn += 1

    logger.debug("Confusion matrix: tp=%d fp=%d tn=%d fn=%d", tp, fp, tn, fn)
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


# ── Helpers ──


def _validate_lengths(actual: list, predicted: list) -> None:
    """Raise ValueError if inputs are invalid."""
    if not actual or not predicted:
        raise ValueError("actual and predicted must be non-empty lists")
    if len(actual) != len(predicted):
        raise ValueError(
            f"Length mismatch: actual has {len(actual)} elements, "
            f"predicted has {len(predicted)}"
        )
