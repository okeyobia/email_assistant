from __future__ import annotations

from collections import deque
from typing import Iterable

from models.email_message import EmailMessage
from services.email_classifier import EmailClassifier
from services.strategies import LabelingStrategy


class DummyStrategy(LabelingStrategy):
    def __init__(self, labels: Iterable[str]):
        self._labels = deque(labels)

    def labels_for(self, email: EmailMessage) -> Iterable[str]:  # noqa: ARG002
        if not self._labels:
            return []
        return [self._labels.popleft()]


def test_email_classifier_merges_strategies():
    email = EmailMessage(
        id="1",
        thread_id=None,
        subject="",
        body="",
        snippet="",
        sender=None,
    )
    classifier = EmailClassifier([DummyStrategy(["Work"]), DummyStrategy(["Finance"])])
    labels = classifier.classify(email)
    assert set(labels) == {"Work", "Finance"}
