from __future__ import annotations

import logging
from typing import Iterable, Sequence, Set

from models.email_message import EmailMessage
from services.strategies import LabelingStrategy

LOGGER = logging.getLogger(__name__)
DEFAULT_LABELS: Set[str] = {"Work", "Personal", "Finance", "Promotions", "Spam"}


class EmailClassifier:
    """Combines multiple labeling strategies (Strategy pattern)."""

    def __init__(self, strategies: Iterable[LabelingStrategy]):
        self._strategies = [strategy for strategy in strategies if strategy]

    def classify(self, email: EmailMessage) -> list[str]:
        labels = set()
        for strategy in self._strategies:
            try:
                produced = list(strategy.labels_for(email))
                LOGGER.debug("%s produced %s for %s", strategy.__class__.__name__, produced, email.id)
                labels.update(produced)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Strategy %s failed: %s", strategy.__class__.__name__, exc)
        filtered = self._filter_allowed_labels(labels)
        LOGGER.info("Email %s classified as %s", email.id, filtered)
        return list(filtered)

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
