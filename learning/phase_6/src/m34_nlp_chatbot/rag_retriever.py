"""
Retrieval-Augmented Generation — document chunking, TF-IDF retrieval, BM25 re-ranking.

WHY THIS MATTERS:
Modern chatbots don't just classify intents — they retrieve relevant
knowledge from a document store and use it to generate accurate answers.
RAG (Retrieval-Augmented Generation) combines information retrieval with
language generation, reducing hallucination by grounding responses in
real documents.

Key concepts:
  - Document chunking: large docs are split into overlapping chunks so
    retrieval can pinpoint the relevant paragraph, not just the doc.
  - TF-IDF retrieval: fast first-pass retrieval using term frequency-
    inverse document frequency similarity.
  - BM25 re-ranking: a more sophisticated scoring function that
    accounts for document length and term saturation.
  - Context assembly: concatenate retrieved chunks up to a token limit
    to form the context window for generation.
"""

import math
import re
from dataclasses import dataclass, field


@dataclass
class Document:
    """A source document for the knowledge base.

    Attributes:
        id: unique document identifier
        title: document title
        content: full text content
        metadata: arbitrary metadata (source, date, category, etc.)
    """
    id: str
    title: str
    content: str
    metadata: dict = field(default_factory=dict)


class DocumentChunker:
    """Split documents into overlapping word-level chunks.

    Overlapping chunks ensure that information at chunk boundaries
    isn't lost. Each chunk retains a reference to its source document
    for attribution.
    """

    def chunk(
        self,
        document: Document,
        chunk_size: int = 200,
        overlap: int = 50,
    ) -> list[dict]:
        """Split document content into overlapping word chunks.

        Args:
            document: source document to chunk
            chunk_size: maximum words per chunk
            overlap: number of overlapping words between consecutive chunks

        Returns:
            List of dicts with keys: doc_id, chunk_index, text, word_count
        """
        words = document.content.split()
        if not words:
            return []

        chunks: list[dict] = []
        step = max(1, chunk_size - overlap)
        chunk_index = 0

        for start in range(0, len(words), step):
            chunk_words = words[start:start + chunk_size]
            chunks.append({
                "doc_id": document.id,
                "chunk_index": chunk_index,
                "text": " ".join(chunk_words),
                "word_count": len(chunk_words),
            })
            chunk_index += 1

            # Stop if we've consumed all words
            if start + chunk_size >= len(words):
                break

        return chunks


class TFIDFRetriever:
    """TF-IDF based document retrieval.

    Builds an inverted index from document chunks and retrieves the
    most similar chunks to a query using cosine similarity over
    TF-IDF vectors.
    """

    def __init__(self):
        self._chunks: list[dict] = []
        self._doc_freq: dict[str, int] = {}
        self._chunk_vectors: list[dict[str, float]] = []

    def _tokenize(self, text: str) -> list[str]:
        """Lowercase tokenization."""
        return re.findall(r'[a-z0-9]+', text.lower())

    def index(self, chunks: list[dict]) -> None:
        """Build TF-IDF index from chunks.

        Computes document frequency across all chunks and pre-computes
        TF-IDF vectors for each chunk.
        """
        self._chunks = chunks
        self._doc_freq = {}

        # Compute document frequency
        for chunk in chunks:
            tokens = set(self._tokenize(chunk["text"]))
            for token in tokens:
                self._doc_freq[token] = self._doc_freq.get(token, 0) + 1

        # Pre-compute TF-IDF vectors for each chunk
        n_docs = len(chunks)
        self._chunk_vectors = []
        for chunk in chunks:
            vec = self._compute_tfidf(chunk["text"], n_docs)
            self._chunk_vectors.append(vec)

    def _compute_tfidf(self, text: str, n_docs: int) -> dict[str, float]:
        """Compute TF-IDF vector for text."""
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        total = len(tokens)
        term_counts: dict[str, int] = {}
        for t in tokens:
            term_counts[t] = term_counts.get(t, 0) + 1

        vec: dict[str, float] = {}
        for term, count in term_counts.items():
            tf = count / total
            df = self._doc_freq.get(term, 0)
            idf = math.log(n_docs / df) if df > 0 else 0.0
            vec[term] = tf * idf

        return vec

    def _cosine_similarity(self, v1: dict[str, float], v2: dict[str, float]) -> float:
        """Cosine similarity between sparse vectors."""
        if not v1 or not v2:
            return 0.0
        shared = set(v1.keys()) & set(v2.keys())
        dot = sum(v1[k] * v2[k] for k in shared)
        n1 = math.sqrt(sum(v * v for v in v1.values()))
        n2 = math.sqrt(sum(v * v for v in v2.values()))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve top-k most similar chunks to the query.

        Returns chunks with an added 'score' key, sorted by
        descending similarity.
        """
        if not self._chunks:
            return []

        n_docs = len(self._chunks)
        query_vec = self._compute_tfidf(query, n_docs)

        scored: list[tuple[float, int]] = []
        for i, chunk_vec in enumerate(self._chunk_vectors):
            sim = self._cosine_similarity(query_vec, chunk_vec)
            scored.append((sim, i))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[dict] = []
        for score, idx in scored[:top_k]:
            chunk = dict(self._chunks[idx])
            chunk["score"] = score
            results.append(chunk)

        return results


class BM25Reranker:
    """BM25 re-ranking for improved retrieval quality.

    BM25 (Best Matching 25) improves on raw TF-IDF by:
      - Term saturation: diminishing returns for repeated terms (k1 param)
      - Length normalization: penalizes very long documents (b param)

    Score for a query term t in document d:
      BM25(t, d) = IDF(t) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * |d|/avgdl))
    """

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r'[a-z0-9]+', text.lower())

    def score(
        self,
        query: str,
        document_text: str,
        k1: float = 1.2,
        b: float = 0.75,
        avgdl: float = None,
    ) -> float:
        """Compute BM25 score for a query against a document.

        Args:
            query: search query
            document_text: document text to score
            k1: term saturation parameter (default 1.2)
            b: length normalization parameter (default 0.75)
            avgdl: average document length. If None, uses len(doc_tokens).

        Returns:
            BM25 score (higher = more relevant)
        """
        query_tokens = self._tokenize(query)
        doc_tokens = self._tokenize(document_text)

        if not query_tokens or not doc_tokens:
            return 0.0

        doc_len = len(doc_tokens)
        if avgdl is None:
            avgdl = doc_len

        # Term frequencies in document
        tf_map: dict[str, int] = {}
        for t in doc_tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        total_score = 0.0
        for qt in query_tokens:
            tf = tf_map.get(qt, 0)
            if tf == 0:
                continue

            # Simplified IDF: log(1 + 1) = log(2) when term exists
            # In practice, IDF would use corpus stats. Here we use a
            # simple positive contribution.
            idf = math.log(2.0)

            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avgdl)
            total_score += idf * numerator / denominator

        return total_score

    def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int = 3,
    ) -> list[dict]:
        """Re-rank chunks using BM25 scoring.

        Args:
            query: search query
            chunks: list of chunk dicts (must have 'text' key)
            top_k: number of top results to return

        Returns:
            Top-k chunks sorted by BM25 score, with 'bm25_score' added.
        """
        if not chunks:
            return []

        # Compute average document length
        total_len = sum(len(self._tokenize(c["text"])) for c in chunks)
        avgdl = total_len / len(chunks) if chunks else 1

        scored: list[tuple[float, int]] = []
        for i, chunk in enumerate(chunks):
            s = self.score(query, chunk["text"], avgdl=avgdl)
            scored.append((s, i))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[dict] = []
        for s, idx in scored[:top_k]:
            chunk = dict(chunks[idx])
            chunk["bm25_score"] = s
            results.append(chunk)

        return results


class ContextAssembler:
    """Assemble retrieved chunks into a context string for generation.

    Given a query and ranked chunks, concatenates chunk text up to a
    token limit to form the context window. Chunks are ordered by
    relevance so the most important information comes first.
    """

    def assemble(
        self,
        query: str,
        retrieved_chunks: list[dict],
        max_tokens: int = 500,
    ) -> str:
        """Assemble context from retrieved chunks.

        Concatenates chunk texts in order, stopping when adding the
        next chunk would exceed max_tokens. Token count is approximated
        as word count.

        Args:
            query: the original query (included as header)
            retrieved_chunks: chunks sorted by relevance
            max_tokens: maximum word count for assembled context

        Returns:
            Assembled context string with query header and chunk texts.
        """
        parts: list[str] = []
        current_tokens = 0

        for chunk in retrieved_chunks:
            chunk_words = chunk["text"].split()
            chunk_len = len(chunk_words)

            if current_tokens + chunk_len > max_tokens:
                # Add partial chunk if we have room
                remaining = max_tokens - current_tokens
                if remaining > 0:
                    parts.append(" ".join(chunk_words[:remaining]))
                break

            parts.append(chunk["text"])
            current_tokens += chunk_len

        return "\n\n".join(parts)
