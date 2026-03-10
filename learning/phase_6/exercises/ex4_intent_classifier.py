"""
Exercise 4: TF-IDF Intent Classification
========================================
Implement a TF-IDF-based intent classifier that takes a query and
training data, then returns the most similar intent using cosine
similarity over TF-IDF vectors.

WHY THIS MATTERS:
Intent classification is the first step in any NLU pipeline. When a
rider sends "I need a ride to the airport", the chatbot must recognize
this as a RIDE_REQUEST intent before it can take action. TF-IDF gives
discriminative word weights — "airport" matters more than "the" — and
cosine similarity finds the closest training example.

Understanding TF-IDF + cosine similarity is foundational for:
  - Search engines (document retrieval)
  - Chatbot intent matching
  - Text classification without neural networks
  - Feature engineering for ML pipelines

YOUR TASK:
1. Implement classify(query, training_data) that:
   a. Tokenizes text into lowercase words (re.findall(r'[a-z0-9]+', text.lower()))
   b. Computes TF = word_count / total_words for each document
   c. Computes IDF = log(N / df) where N = total training docs, df = docs containing term
   d. Builds TF-IDF vectors for the query and each training doc
   e. Finds the training doc with highest cosine similarity
   f. Returns (intent_name, similarity_score)

Formula reference:
  TF-IDF(term, doc) = TF(term, doc) * IDF(term)
  cosine_sim(v1, v2) = dot(v1, v2) / (||v1|| * ||v2||)
"""

import math
import re


def classify(query: str, training_data: dict[str, list[str]]) -> tuple[str, float]:
    """Classify a query by finding the most similar training document.

    Args:
        query: the user's input text (e.g., "book a ride to the airport")
        training_data: dict mapping intent names to lists of training
                       examples. E.g.:
                       {
                           "ride_request": ["book a ride", "I need a car"],
                           "fare_inquiry": ["how much does it cost", "what is the fare"],
                       }

    Returns:
        (intent_name, similarity_score) — the intent with the highest
        cosine similarity to the query. Returns ("unknown", 0.0) if
        no training data or no similarity.

    Steps:
    1. Flatten all training examples into a list of (intent, text) pairs
    2. Compute document frequency (df) for each term across ALL training docs
    3. For the query and each training doc, compute TF-IDF vectors
    4. Find the training doc with highest cosine similarity to the query
    5. Return its intent name and the similarity score
    """
    # YOUR CODE HERE (~30 lines)
    raise NotImplementedError("Implement classify")


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    training_data = {
        "ride_request": [
            "book a ride to the airport",
            "I need a car to downtown",
            "get me a taxi to central station",
        ],
        "fare_inquiry": [
            "how much does a ride cost",
            "what is the fare to the airport",
            "estimate the price for this trip",
        ],
        "greeting": [
            "hello how are you",
            "hi there good morning",
            "hey what is up",
        ],
        "complaint": [
            "the driver was rude and late",
            "terrible ride experience bad driver",
            "my driver took a wrong route and overcharged",
        ],
    }

    # Test 1: ride request classification
    intent, score = classify("I want to book a ride", training_data)
    assert intent == "ride_request", f"Expected 'ride_request', got '{intent}'"
    assert score > 0.0, f"Expected positive score, got {score}"
    print(f"[PASS] 'I want to book a ride' -> {intent} (score={score:.3f})")

    # Test 2: fare inquiry
    intent, score = classify("how much will this cost", training_data)
    assert intent == "fare_inquiry", f"Expected 'fare_inquiry', got '{intent}'"
    print(f"[PASS] 'how much will this cost' -> {intent} (score={score:.3f})")

    # Test 3: complaint
    intent, score = classify("the driver was very rude", training_data)
    assert intent == "complaint", f"Expected 'complaint', got '{intent}'"
    print(f"[PASS] 'the driver was very rude' -> {intent} (score={score:.3f})")

    # Test 4: greeting
    intent, score = classify("hello there", training_data)
    assert intent == "greeting", f"Expected 'greeting', got '{intent}'"
    print(f"[PASS] 'hello there' -> {intent} (score={score:.3f})")

    # Test 5: empty training data
    intent, score = classify("anything", {})
    assert intent == "unknown" and score == 0.0, \
        f"Expected ('unknown', 0.0), got ('{intent}', {score})"
    print("[PASS] Empty training data returns ('unknown', 0.0)")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
