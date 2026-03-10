"""
Intent Classification — keyword matching, TF-IDF, and multi-intent detection.

WHY THIS MATTERS:
Chatbots in ride-sharing platforms must understand what a user wants:
booking a ride, checking status, filing a complaint, etc. Intent
classification is the first step in any NLU pipeline. Understanding how
keyword matching evolves into TF-IDF-based statistical classification
shows the progression from simple heuristics to real ML-adjacent methods.

Key concepts:
  - Keyword matching: fast, interpretable, but fragile.
  - TF-IDF: term frequency-inverse document frequency weights rare,
    discriminative words higher than common ones.
  - Cosine similarity: measures angle between TF-IDF vectors, ignoring
    magnitude — a query about "ride cost" is close to "fare inquiry"
    regardless of document length.
  - Multi-intent detection: a single message like "Book a ride and check
    my last fare" contains two intents.
"""

import math
import re
from enum import Enum


class IntentType(Enum):
    """Supported intent types for ride-sharing chatbot."""
    GREETING = "greeting"
    FAREWELL = "farewell"
    RIDE_REQUEST = "ride_request"
    RIDE_STATUS = "ride_status"
    FARE_INQUIRY = "fare_inquiry"
    COMPLAINT = "complaint"
    PAYMENT = "payment"
    SAFETY = "safety"
    FAQ = "faq"
    UNKNOWN = "unknown"


class KeywordMatcher:
    """Keyword-based intent matching.

    The simplest approach: define a set of keywords for each intent and
    check how many keywords appear in the user's message. Confidence is
    the fraction of registered keywords that matched.

    Limitations:
      - Cannot handle synonyms or paraphrases not in the keyword list.
      - No understanding of word importance (all keywords equal).
      - Breaks on ambiguous phrases.
    """

    def __init__(self):
        self._intents: dict[IntentType, list[str]] = {}

    def add_intent(self, intent_type: IntentType, keywords: list[str]) -> None:
        """Register keywords for an intent type.

        Keywords are stored lowercase for case-insensitive matching.
        """
        self._intents[intent_type] = [kw.lower() for kw in keywords]

    def match(self, text: str) -> tuple[IntentType, float]:
        """Match text against registered intents.

        Returns (best_intent, confidence) where confidence is the
        fraction of the intent's keywords found in the text.
        Case-insensitive matching. Returns (UNKNOWN, 0.0) if no
        keywords match any intent.
        """
        text_lower = text.lower()
        best_intent = IntentType.UNKNOWN
        best_confidence = 0.0

        for intent_type, keywords in self._intents.items():
            if not keywords:
                continue
            matched = sum(1 for kw in keywords if kw in text_lower)
            confidence = matched / len(keywords)
            if confidence > best_confidence:
                best_confidence = confidence
                best_intent = intent_type

        return (best_intent, best_confidence)


class TFIDFClassifier:
    """TF-IDF based intent classification.

    Builds TF-IDF vectors from training documents and classifies new
    text by finding the most similar training document via cosine
    similarity.

    TF (Term Frequency) = count of term in document / total words in document
    IDF (Inverse Document Frequency) = log(N / df) where N = total docs,
        df = number of docs containing the term.

    This gives high weight to words that are frequent in a specific
    document but rare across all documents — exactly the discriminative
    words we want for classification.
    """

    def __init__(self):
        self._documents: list[tuple[IntentType, str]] = []

    def add_document(self, intent_type: IntentType, text: str) -> None:
        """Add a training document for the given intent."""
        self._documents.append((intent_type, text))

    def _tokenize(self, text: str) -> list[str]:
        """Split text into lowercase tokens, stripping non-alphanumeric."""
        return re.findall(r'[a-z0-9]+', text.lower())

    def _compute_tfidf(self, text: str) -> dict[str, float]:
        """Compute TF-IDF vector for text against the training corpus.

        TF = count of term in text / total words in text
        IDF = log(N / df) where N = total documents, df = documents
              containing the term. If df == 0, IDF = 0.
        """
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        total_words = len(tokens)
        term_counts: dict[str, int] = {}
        for token in tokens:
            term_counts[token] = term_counts.get(token, 0) + 1

        n_docs = len(self._documents)
        if n_docs == 0:
            return {term: count / total_words for term, count in term_counts.items()}

        # Document frequency: how many training docs contain each term
        doc_freq: dict[str, int] = {}
        for _, doc_text in self._documents:
            doc_tokens = set(self._tokenize(doc_text))
            for token in doc_tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        tfidf: dict[str, float] = {}
        for term, count in term_counts.items():
            tf = count / total_words
            df = doc_freq.get(term, 0)
            idf = math.log(n_docs / df) if df > 0 else 0.0
            tfidf[term] = tf * idf

        return tfidf

    def _cosine_similarity(self, vec1: dict[str, float], vec2: dict[str, float]) -> float:
        """Compute cosine similarity between two sparse vectors.

        cosine_sim = dot(v1, v2) / (||v1|| * ||v2||)
        Returns 0.0 if either vector is zero.
        """
        if not vec1 or not vec2:
            return 0.0

        # Dot product over shared keys
        shared_keys = set(vec1.keys()) & set(vec2.keys())
        dot_product = sum(vec1[k] * vec2[k] for k in shared_keys)

        norm1 = math.sqrt(sum(v * v for v in vec1.values()))
        norm2 = math.sqrt(sum(v * v for v in vec2.values()))

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def classify(self, text: str) -> tuple[IntentType, float]:
        """Classify text by finding the most similar training document.

        Returns (intent_type, similarity_score). If no documents are
        registered, returns (UNKNOWN, 0.0).
        """
        if not self._documents:
            return (IntentType.UNKNOWN, 0.0)

        query_vec = self._compute_tfidf(text)
        best_intent = IntentType.UNKNOWN
        best_score = 0.0

        for intent_type, doc_text in self._documents:
            doc_vec = self._compute_tfidf(doc_text)
            similarity = self._cosine_similarity(query_vec, doc_vec)
            if similarity > best_score:
                best_score = similarity
                best_intent = intent_type

        return (best_intent, best_score)


class MultiIntentDetector:
    """Detect multiple intents in a single message.

    Splits the message by sentence boundaries (. ! ?) and classifies
    each sentence independently. Returns all intents above a confidence
    threshold. This handles messages like "Book me a ride. Also, what's
    the fare to the airport?"
    """

    def detect(
        self,
        text: str,
        classifier: TFIDFClassifier,
        threshold: float = 0.3,
    ) -> list[tuple[IntentType, float]]:
        """Detect multiple intents by classifying each sentence.

        Splits text on sentence boundaries (. ! ?), classifies each
        fragment, and returns intents with confidence >= threshold.
        Deduplicates by keeping the highest confidence per intent type.
        """
        # Split on sentence boundaries, keep non-empty fragments
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return []

        intent_scores: dict[IntentType, float] = {}
        for sentence in sentences:
            intent_type, score = classifier.classify(sentence)
            if score >= threshold:
                if intent_type not in intent_scores or score > intent_scores[intent_type]:
                    intent_scores[intent_type] = score

        return [(intent, score) for intent, score in intent_scores.items()]
