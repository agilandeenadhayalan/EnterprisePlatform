"""
Domain models for the Sentiment Analysis service.
"""


class SentimentResult:
    """A sentiment analysis result."""

    def __init__(
        self,
        id: str,
        text: str,
        sentiment: str,
        score: float,
        aspects: list[dict],
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.text = text
        self.sentiment = sentiment
        self.score = score
        self.aspects = aspects
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "sentiment": self.sentiment,
            "score": self.score,
            "aspects": self.aspects,
            "created_at": self.created_at,
        }


class AspectSentiment:
    """Sentiment for a specific aspect."""

    def __init__(
        self,
        aspect: str,
        sentiment: str,
        score: float,
    ):
        self.aspect = aspect
        self.sentiment = sentiment
        self.score = score

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect,
            "sentiment": self.sentiment,
            "score": self.score,
        }


class ReviewAnalysis:
    """A review analysis with aspect sentiments."""

    def __init__(
        self,
        id: str,
        review_id: str,
        entity_type: str,
        entity_id: str,
        overall_sentiment: str,
        aspects: list[dict],
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.review_id = review_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.overall_sentiment = overall_sentiment
        self.aspects = aspects
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "review_id": self.review_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "overall_sentiment": self.overall_sentiment,
            "aspects": self.aspects,
            "created_at": self.created_at,
        }
