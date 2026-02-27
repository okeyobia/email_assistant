from __future__ import annotations

from typing import Iterable

from models.email_message import EmailMessage
from services.ml_classifier import MLClassifier

from .base import LabelingStrategy


class MLStrategy(LabelingStrategy):
    """Strategy that delegates to an ML classifier if available."""

    def __init__(self, classifier: MLClassifier):
        self._classifier = classifier

    def labels_for(self, email: EmailMessage) -> Iterable[str]:
        prediction = self._classifier.predict(f"{email.subject}\n{email.body}") if self._classifier.is_ready else None
        return [prediction] if prediction else []
