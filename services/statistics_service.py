from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Dict, Mapping

LOGGER = logging.getLogger(__name__)


class StatisticsService:
    """Very small JSON-backed stats store."""

    def __init__(self, stats_file: Path):
        self._stats_file = stats_file
        self._stats_file.touch(exist_ok=True)
        if not self._stats_file.read_text().strip():
            self._stats_file.write_text(json.dumps({}), encoding="utf-8")

    def _read(self) -> Dict:
        try:
            return json.loads(self._stats_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("Stats file was corrupt, resetting %s", self._stats_file)
            self._stats_file.write_text(json.dumps({}), encoding="utf-8")
            return {}

    def _write(self, payload: Dict) -> None:
        self._stats_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def record_fetch(self, account: str, count: int) -> None:
        stats = self._read()
        stats["fetch_runs"] = stats.get("fetch_runs", 0) + 1
        stats["emails_seen"] = stats.get("emails_seen", 0) + count
        bucket = self._account_bucket(stats, account)
        bucket["fetch_runs"] = bucket.get("fetch_runs", 0) + 1
        bucket["emails_seen"] = bucket.get("emails_seen", 0) + count
        self._write(stats)

    def record_label_application(self, account: str, label_counts: Mapping[str, int]) -> None:
        stats = self._read()
        stats["label_runs"] = stats.get("label_runs", 0) + 1
        labels = Counter(stats.get("labels", {}))
        for label, count in label_counts.items():
            labels[label] += count
        stats["labels"] = dict(labels)

        bucket = self._account_bucket(stats, account)
        bucket["label_runs"] = bucket.get("label_runs", 0) + 1
        bucket_labels = Counter(bucket.get("labels", {}))
        for label, count in label_counts.items():
            bucket_labels[label] += count
        bucket["labels"] = dict(bucket_labels)

        self._write(stats)

    def snapshot(self) -> Dict:
        return self._read()

    def _account_bucket(self, stats: Dict, account: str) -> Dict:
        accounts = stats.setdefault("accounts", {})
        return accounts.setdefault(account, {})
