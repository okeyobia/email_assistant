from __future__ import annotations

from dataclasses import dataclass

from models.email_message import EmailMessage

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError as exc:  # pragma: no cover - handled via dependency management
    raise RuntimeError("Install vaderSentiment to use sentiment analysis features") from exc


@dataclass(slots=True)
class SentimentResult:
    label: str
    compound: float


class SentimentService:
    """Provides sentiment classification via VADER."""

    def __init__(self) -> None:
        self._analyzer = SentimentIntensityAnalyzer()

    def analyze(self, email: EmailMessage) -> SentimentResult:
        text = " \n".join(filter(None, [email.subject, email.snippet, email.body]))
        scores = self._analyzer.polarity_scores(text or "")
        compound = scores.get("compound", 0.0)
        label = self._label_from_score(compound)
        return SentimentResult(label=label, compound=compound)

    def _label_from_score(self, score: float) -> str:
        if score >= 0.05:
            return "Positive"
        if score <= -0.05:
            return "Negative"
        return "Neutral"
