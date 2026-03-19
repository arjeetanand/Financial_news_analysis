from __future__ import annotations

from dataclasses import dataclass

from mlops.entity_linking import EntityLinker


POSITIVE_KEYWORDS = {
    "gain",
    "gains",
    "surge",
    "profit",
    "upbeat",
    "beat",
    "growth",
    "rally",
    "bullish",
}
NEGATIVE_KEYWORDS = {
    "fall",
    "falls",
    "drop",
    "loss",
    "miss",
    "weak",
    "decline",
    "slump",
    "bearish",
}


@dataclass
class SentimentPrediction:
    label: str
    confidence: float


class InferenceService:
    """Open-source inference helpers for serving lightweight API predictions."""

    def __init__(self, entity_linker: EntityLinker) -> None:
        self.entity_linker = entity_linker

    def predict_sentiment(self, text: str) -> SentimentPrediction:
        tokens = set(str(text).lower().split())
        positive_hits = len(tokens & POSITIVE_KEYWORDS)
        negative_hits = len(tokens & NEGATIVE_KEYWORDS)

        if positive_hits > negative_hits:
            confidence = min(1.0, 0.5 + 0.1 * positive_hits)
            return SentimentPrediction(label="Positive", confidence=confidence)
        if negative_hits > positive_hits:
            confidence = min(1.0, 0.5 + 0.1 * negative_hits)
            return SentimentPrediction(label="Negative", confidence=confidence)
        return SentimentPrediction(label="Neutral", confidence=0.5)

    def predict_entities(self, text: str) -> list[dict[str, str | float]]:
        return [m.__dict__ for m in self.entity_linker.link_text(text)]

    def predict_news(self, headline: str, summary: str) -> dict:
        combined = f"{headline} {summary}".strip()
        sentiment = self.predict_sentiment(combined)
        entities = self.predict_entities(combined)
        return {
            "sentiment": sentiment.__dict__,
            "entities": entities,
            "entity_count": len(entities),
        }
