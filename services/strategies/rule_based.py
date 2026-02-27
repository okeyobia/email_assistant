from __future__ import annotations

from typing import Iterable

from models.email_message import EmailMessage
from utils.rules_engine import RulesEngine

from .base import LabelingStrategy


class RuleBasedStrategy(LabelingStrategy):
    """Keyword-driven labeling strategy."""

    def __init__(self, rules_engine: RulesEngine):
        self._rules_engine = rules_engine

    def labels_for(self, email: EmailMessage) -> Iterable[str]:
        return self._rules_engine.match(email)
