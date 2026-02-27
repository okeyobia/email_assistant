from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass(slots=True)
class EmailMessage:
    """Simplified representation of a Gmail message."""

    id: str
    thread_id: str | None
    subject: str
    body: str
    snippet: str
    sender: str | None = None
    labels: List[str] = field(default_factory=list)
    received_at: datetime | None = None
