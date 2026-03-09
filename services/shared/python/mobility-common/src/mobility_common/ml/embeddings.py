"""
Vector similarity and embedding utilities.

Provides pure-Python implementations of common vector operations used
with embedding models and similarity search.  No external dependencies
(numpy, scipy) are required — all calculations use the ``math``
standard-library module.

Functions
---------
- :func:`cosine_similarity`   Cosine similarity between two vectors.
- :func:`euclidean_distance`  Euclidean (L2) distance between two vectors.
- :func:`normalize_vector`    L2-normalise a vector to unit length.
- :func:`find_k_nearest`      Find *k* most similar vectors from a candidate set.
"""

from __future__ import annotations

import logging
import math
from typing import List, Tuple

logger = logging.getLogger(__name__)

__all__ = [
    "cosine_similarity",
    "euclidean_distance",
    "normalize_vector",
    "find_k_nearest",
]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute the cosine similarity between two vectors.

    Cosine similarity measures the cosine of the angle between two
    vectors, ranging from -1 (opposite) through 0 (orthogonal) to
    1 (identical direction).

    Parameters
    ----------
    vec_a : list[float]
        First vector.
    vec_b : list[float]
        Second vector (must have the same dimensionality as *vec_a*).

    Returns
    -------
    float
        Cosine similarity in [-1, 1].

    Raises
    ------
    ValueError
        If vectors are empty or have different lengths.
    """
    _validate_vectors(vec_a, vec_b)

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        logger.warning(
            "Cosine similarity: zero-magnitude vector — returning 0.0"
        )
        return 0.0

    result = dot / (norm_a * norm_b)
    # Clamp to [-1, 1] to handle floating-point imprecision
    result = max(-1.0, min(1.0, result))
    logger.debug("Cosine similarity = %.6f (dim=%d)", result, len(vec_a))
    return result


def euclidean_distance(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute the Euclidean (L2) distance between two vectors.

    Parameters
    ----------
    vec_a : list[float]
        First vector.
    vec_b : list[float]
        Second vector (must have the same dimensionality as *vec_a*).

    Returns
    -------
    float
        Non-negative distance.  0 means the vectors are identical.

    Raises
    ------
    ValueError
        If vectors are empty or have different lengths.
    """
    _validate_vectors(vec_a, vec_b)

    result = math.sqrt(sum((a - b) ** 2 for a, b in zip(vec_a, vec_b)))
    logger.debug("Euclidean distance = %.6f (dim=%d)", result, len(vec_a))
    return result


def normalize_vector(vec: List[float]) -> List[float]:
    """L2-normalise a vector to unit length.

    After normalisation, the vector has magnitude 1.0, which is useful
    when you want cosine similarity to equal the dot product.

    Parameters
    ----------
    vec : list[float]
        Input vector.

    Returns
    -------
    list[float]
        Unit vector in the same direction.  Returns a zero vector if
        the input has zero magnitude.

    Raises
    ------
    ValueError
        If the vector is empty.
    """
    if not vec:
        raise ValueError("Cannot normalise an empty vector")

    magnitude = math.sqrt(sum(v * v for v in vec))

    if magnitude == 0:
        logger.warning(
            "normalize_vector: zero-magnitude vector — returning zeros"
        )
        return [0.0] * len(vec)

    result = [v / magnitude for v in vec]
    logger.debug("Normalised vector (dim=%d, magnitude=%.6f)", len(vec), magnitude)
    return result


def find_k_nearest(
    query_vec: List[float],
    candidates: List[List[float]],
    k: int = 5,
) -> List[Tuple[int, float]]:
    """Find the *k* most similar vectors from a candidate set.

    Uses cosine similarity to rank candidates.  Results are returned in
    descending order of similarity (most similar first).

    Parameters
    ----------
    query_vec : list[float]
        The query embedding vector.
    candidates : list[list[float]]
        List of candidate vectors to search through.
    k : int
        Number of nearest neighbours to return (default 5).

    Returns
    -------
    list[tuple[int, float]]
        Up to *k* tuples of ``(candidate_index, similarity_score)``,
        sorted by similarity descending.

    Raises
    ------
    ValueError
        If *query_vec* is empty or *k* < 1.
    """
    if not query_vec:
        raise ValueError("Query vector must be non-empty")
    if k < 1:
        raise ValueError("k must be >= 1")
    if not candidates:
        logger.debug("find_k_nearest: no candidates — returning empty")
        return []

    similarities: List[Tuple[int, float]] = []
    for idx, candidate in enumerate(candidates):
        if len(candidate) != len(query_vec):
            logger.warning(
                "Skipping candidate %d: dimension mismatch (%d vs %d)",
                idx,
                len(candidate),
                len(query_vec),
            )
            continue
        sim = cosine_similarity(query_vec, candidate)
        similarities.append((idx, sim))

    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)

    result = similarities[:k]
    logger.debug(
        "find_k_nearest: %d candidates searched, returning top %d",
        len(similarities),
        len(result),
    )
    return result


# ── Helpers ──


def _validate_vectors(vec_a: List[float], vec_b: List[float]) -> None:
    """Raise ValueError if vector inputs are invalid."""
    if not vec_a or not vec_b:
        raise ValueError("Vectors must be non-empty")
    if len(vec_a) != len(vec_b):
        raise ValueError(
            f"Dimension mismatch: vec_a has {len(vec_a)} elements, "
            f"vec_b has {len(vec_b)}"
        )
