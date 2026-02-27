from __future__ import annotations

import json
from pathlib import Path

from models.email_message import EmailMessage
from utils.rules_engine import RulesEngine


def _build_rules(tmp_path: Path) -> Path:
    rules_path = tmp_path / "rules.json"
    payload = {
        "rules": [
            {"label": "Work", "keywords": ["project"], "priority": 2},
            {"label": "Finance", "keywords": ["invoice"], "priority": 5},
        ]
    }
    rules_path.write_text(json.dumps(payload), encoding="utf-8")
    return rules_path


def test_rules_engine_matches_subject(tmp_path: Path) -> None:
    rules_path = _build_rules(tmp_path)
    engine = RulesEngine(rules_path)
    email = EmailMessage(
        id="1",
        thread_id=None,
        subject="Invoice for project",
        body="",
        snippet="",
        sender=None,
    )
    labels = engine.match(email)
    assert labels == ["Finance", "Work"]
