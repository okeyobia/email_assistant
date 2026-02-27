from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Sequence, Set

from models.email_message import EmailMessage
from services.ml_classifier import MLClassifier
from utils.rules_engine import RulesEngine

LOGGER = logging.getLogger(__name__)
DEFAULT_LABELS: Set[str] = {"Work", "Personal", "Finance", "Promotions", "Spam"}


class EmailClassifier:
    """Combine rules and optional ML predictions."""

    def __init__(self, rules_engine: RulesEngine, ml_classifier: Optional[MLClassifier] = None):
        self.rules_engine = rules_engine
        self.ml_classifier = ml_classifier

    def classify(self, email: EmailMessage) -> List[str]:
        labels = set(self.rules_engine.match(email))
        LOGGER.debug("Rule-based labels for %s: %s", email.id, labels)
        prediction = self._ml_prediction(email)
        if prediction:
            labels.add(prediction)
        filtered = self._filter_allowed_labels(labels)
        LOGGER.info("Email %s classified as %s", email.id, filtered)
        return sorted(filtered)

    def _ml_prediction(self, email: EmailMessage) -> Optional[str]:
        if not self.ml_classifier or not self.ml_classifier.is_ready:
            return None
        text = f"{email.subject}\n{email.body}"
        try:
            prediction = self.ml_classifier.predict(text)
            if prediction:
                LOGGER.debug("ML predicted %s for %s", prediction, email.id)
            return prediction
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("ML prediction failed: %s", exc)
            return None

    def _filter_allowed_labels(self, labels: Iterable[str]) -> Sequence[str]:
        cleaned = set()
        for label in labels:
            normalized = label.strip()
            if not normalized:
                continue
            if normalized.lower() in {value.lower() for value in DEFAULT_LABELS}:
                cleaned.add(self._canonical_name(normalized))
            else:
                cleaned.add(normalized)
        return sorted(cleaned)

    def _canonical_name(self, name: str) -> str:
        lookup = {value.lower(): value for value in DEFAULT_LABELS}
        return lookup.get(name.lower(), name)
