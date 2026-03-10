"""
In-memory sentiment analysis repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone

from models import SentimentResult, ReviewAnalysis


POSITIVE_WORDS = {"great", "excellent", "amazing", "good", "love", "wonderful", "fantastic", "happy", "best", "awesome", "nice", "perfect", "comfortable", "clean", "friendly", "fast", "smooth"}
NEGATIVE_WORDS = {"bad", "terrible", "awful", "hate", "worst", "horrible", "poor", "dirty", "slow", "rude", "broken", "late", "expensive", "dangerous", "uncomfortable", "disappointing"}

ASPECT_KEYWORDS = {
    "driver": ["driver", "chauffeur"],
    "vehicle": ["car", "vehicle", "seat", "interior"],
    "price": ["price", "fare", "cost", "expensive", "cheap"],
    "wait_time": ["wait", "waiting", "late", "delay", "pickup"],
    "app": ["app", "application", "interface", "booking"],
}


class SentimentAnalysisRepository:
    """In-memory store for sentiment results and review analyses."""

    def __init__(self, seed: bool = False):
        self.results: list[SentimentResult] = []
        self.reviews: list[ReviewAnalysis] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        results = [
            SentimentResult("sent-001", "Great ride, very comfortable and clean car", "positive", 0.92, [{"aspect": "vehicle", "sentiment": "positive", "score": 0.95}], now),
            SentimentResult("sent-002", "The driver was excellent and very friendly", "positive", 0.88, [{"aspect": "driver", "sentiment": "positive", "score": 0.90}], now),
            SentimentResult("sent-003", "Amazing experience, will use again", "positive", 0.95, [], now),
            SentimentResult("sent-004", "Terrible wait time, driver was late", "negative", 0.15, [{"aspect": "wait_time", "sentiment": "negative", "score": 0.10}], now),
            SentimentResult("sent-005", "The car was dirty and uncomfortable", "negative", 0.12, [{"aspect": "vehicle", "sentiment": "negative", "score": 0.08}], now),
            SentimentResult("sent-006", "Bad experience, rude driver", "negative", 0.18, [{"aspect": "driver", "sentiment": "negative", "score": 0.15}], now),
            SentimentResult("sent-007", "It was okay, nothing special", "neutral", 0.50, [], now),
            SentimentResult("sent-008", "Average ride, fair price", "neutral", 0.55, [{"aspect": "price", "sentiment": "neutral", "score": 0.50}], now),
        ]
        self.results.extend(results)

        reviews = [
            ReviewAnalysis("rev-001", "review-101", "driver", "driver-A", "positive", [{"aspect": "driver", "sentiment": "positive", "score": 0.90}, {"aspect": "vehicle", "sentiment": "positive", "score": 0.85}], now),
            ReviewAnalysis("rev-002", "review-102", "driver", "driver-B", "negative", [{"aspect": "driver", "sentiment": "negative", "score": 0.15}, {"aspect": "wait_time", "sentiment": "negative", "score": 0.20}], now),
            ReviewAnalysis("rev-003", "review-103", "route", "route-A", "positive", [{"aspect": "price", "sentiment": "positive", "score": 0.80}], now),
            ReviewAnalysis("rev-004", "review-104", "driver", "driver-C", "neutral", [{"aspect": "driver", "sentiment": "neutral", "score": 0.50}], now),
            ReviewAnalysis("rev-005", "review-105", "route", "route-B", "negative", [{"aspect": "price", "sentiment": "negative", "score": 0.20}, {"aspect": "wait_time", "sentiment": "negative", "score": 0.15}], now),
            ReviewAnalysis("rev-006", "review-106", "driver", "driver-A", "positive", [{"aspect": "driver", "sentiment": "positive", "score": 0.88}, {"aspect": "app", "sentiment": "positive", "score": 0.75}], now),
        ]
        self.reviews.extend(reviews)

    # ── Analysis ──

    def analyze_text(self, text: str) -> SentimentResult:
        result_id = f"sent-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        words = set(text.lower().split())
        pos_count = len(words & POSITIVE_WORDS)
        neg_count = len(words & NEGATIVE_WORDS)

        if pos_count > neg_count:
            sentiment = "positive"
            score = min(0.5 + pos_count * 0.15, 0.99)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = max(0.5 - neg_count * 0.15, 0.01)
        else:
            sentiment = "neutral"
            score = 0.50

        # Extract aspects
        aspects = []
        for aspect, keywords in ASPECT_KEYWORDS.items():
            if any(kw in text.lower() for kw in keywords):
                aspects.append({"aspect": aspect, "sentiment": sentiment, "score": score})

        result = SentimentResult(result_id, text, sentiment, score, aspects, now)
        self.results.append(result)
        return result

    def analyze_review(self, data: dict) -> ReviewAnalysis:
        rev_id = f"rev-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        # Analyze text for sentiment
        text = data["text"]
        words = set(text.lower().split())
        pos_count = len(words & POSITIVE_WORDS)
        neg_count = len(words & NEGATIVE_WORDS)

        if pos_count > neg_count:
            overall = "positive"
            base_score = min(0.5 + pos_count * 0.15, 0.99)
        elif neg_count > pos_count:
            overall = "negative"
            base_score = max(0.5 - neg_count * 0.15, 0.01)
        else:
            overall = "neutral"
            base_score = 0.50

        aspects = []
        for aspect, keywords in ASPECT_KEYWORDS.items():
            if any(kw in text.lower() for kw in keywords):
                aspects.append({"aspect": aspect, "sentiment": overall, "score": base_score})

        review = ReviewAnalysis(rev_id, data["review_id"], data["entity_type"], data["entity_id"], overall, aspects, now)
        self.reviews.append(review)
        return review

    # ── Results ──

    def list_results(self, sentiment: str | None = None) -> list[SentimentResult]:
        result = list(self.results)
        if sentiment:
            result = [r for r in result if r.sentiment == sentiment]
        return result

    def get_result(self, result_id: str) -> SentimentResult | None:
        for r in self.results:
            if r.id == result_id:
                return r
        return None

    # ── Reviews ──

    def list_reviews(self) -> list[ReviewAnalysis]:
        return list(self.reviews)

    def get_review(self, review_id: str) -> ReviewAnalysis | None:
        for r in self.reviews:
            if r.id == review_id:
                return r
        return None

    # ── Stats ──

    def get_stats(self) -> dict:
        by_sentiment: dict[str, int] = {}
        total_score = 0.0
        for r in self.results:
            by_sentiment[r.sentiment] = by_sentiment.get(r.sentiment, 0) + 1
            total_score += r.score
        avg_score = total_score / len(self.results) if self.results else 0.0
        return {
            "total_analyses": len(self.results),
            "by_sentiment": by_sentiment,
            "avg_score": round(avg_score, 4),
        }


REPO_CLASS = SentimentAnalysisRepository
repo = SentimentAnalysisRepository(seed=True)
