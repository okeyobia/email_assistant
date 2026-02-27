from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class Rule:
    """Keyword-based rule definition for labeling."""

    label: str
    keywords: List[str]
    match_subject: bool = True
    match_body: bool = True
    priority: int = 0

    def normalized_keywords(self) -> List[str]:
        return [kw.lower() for kw in self.keywords]
