from __future__ import annotations

from services.persistence_service import ProcessedStore


def test_processed_store_roundtrip(tmp_path):
    db_path = tmp_path / "emails.db"
    store = ProcessedStore(db_path)

    assert store.is_processed("acct", "abc") is False

    store.mark_processed("acct", "abc")
    assert store.is_processed("acct", "abc") is True

    # Other accounts should not collide
    assert store.is_processed("other", "abc") is False
