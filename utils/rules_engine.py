from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from models.email_message import EmailMessage
from models.rule import Rule


class RulesEngine:
    """Simple keyword-based rules loader and matcher."""

    def __init__(self, rules_file: Path):
        self.rules_file = rules_file
        self._rules: List[Rule] = []
        self.reload()

    def reload(self) -> None:
        if not self.rules_file.exists():
            raise FileNotFoundError(f"Missing rules file: {self.rules_file}")
        data = json.loads(self.rules_file.read_text(encoding="utf-8"))
        rules: Iterable[dict] = data.get("rules", [])
        self._rules = [
            Rule(
                label=item["label"],
                keywords=item.get("keywords", []),
                match_subject=item.get("match_subject", True),
                match_body=item.get("match_body", True),
                priority=item.get("priority", 0),
            )
            for item in rules
        ]

    def match(self, email: EmailMessage) -> List[str]:
        subject = (email.subject or "").lower()
        body = (email.body or "").lower()
        matches: List[str] = []
        for rule in sorted(self._rules, key=lambda r: r.priority, reverse=True):
            keywords = rule.normalized_keywords()
            subject_hit = rule.match_subject and any(kw in subject for kw in keywords)
            body_hit = rule.match_body and any(kw in body for kw in keywords)
            if subject_hit or body_hit:
                matches.append(rule.label)
        return matches
