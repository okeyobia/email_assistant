from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from models.email_message import EmailMessage


class LabelingStrategy(ABC):
    """Strategy interface for deriving labels from an email."""

    @abstractmethod
    def labels_for(self, email: EmailMessage) -> Iterable[str]:
        """Return zero or more labels for the supplied email."""
        raise NotImplementedError
