from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(slots=True)
class AccountConfig:
    name: str
    credentials_file: Path
    token_file: Path
    user_id: str


@dataclass(slots=True)
class AppConfig:
    rules_file: Path
    log_dir: Path
    log_level: str
    fetch_batch_size: int
    stats_file: Path
    model_path: Optional[Path]
    transformer_model: Optional[str]
    db_path: Path
    accounts: Dict[str, AccountConfig]
    default_account: AccountConfig
    accounts_file: Path

    def get_account(self, account_name: Optional[str]) -> AccountConfig:
        if not account_name:
            return self.default_account
        if account_name not in self.accounts:
            available = ", ".join(sorted(self.accounts))
            raise KeyError(f"Unknown account '{account_name}'. Available accounts: {available}")
        return self.accounts[account_name]


def _resolve_path(value: str | None, fallback: str) -> Path:
    candidate = Path(value or fallback)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate


def _maybe_write_secret_file(target: Path, inline_value: str | None, b64_value: str | None) -> None:
    if not inline_value and not b64_value:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if inline_value:
        target.write_text(inline_value, encoding="utf-8")
        return
    try:
        decoded = base64.b64decode(b64_value or "")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Failed to decode base64 secret payload") from exc
    target.write_bytes(decoded)


def load_config(env_file: str | os.PathLike[str] | None = None) -> AppConfig:
    """Load configuration values from a .env file and environment variables."""

    if env_file:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    credentials_file = _resolve_path(os.getenv("GOOGLE_CLIENT_SECRETS"), "credentials.json")
    token_file = _resolve_path(os.getenv("GOOGLE_TOKEN_PATH"), "token.json")
    rules_file = _resolve_path(os.getenv("RULES_FILE"), "rules/rules.json")
    log_dir = _resolve_path(os.getenv("LOG_DIR"), "logs")
    stats_file = _resolve_path(os.getenv("STATS_FILE"), "data/stats.json")
    db_path = _resolve_path(os.getenv("DB_PATH"), "data/email_assistant.db")
    accounts_file = _resolve_path(os.getenv("GMAIL_ACCOUNTS_FILE"), "accounts.json")

    log_dir.mkdir(parents=True, exist_ok=True)
    stats_file.parent.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _maybe_write_secret_file(
        credentials_file,
        os.getenv("GOOGLE_CLIENT_SECRETS_JSON"),
        os.getenv("GOOGLE_CLIENT_SECRETS_B64"),
    )
    _maybe_write_secret_file(
        token_file,
        os.getenv("GOOGLE_TOKEN_JSON"),
        os.getenv("GOOGLE_TOKEN_B64"),
    )

    fetch_batch_size = int(os.getenv("FETCH_BATCH_SIZE", "25"))

    model_path = os.getenv("ML_MODEL_PATH")
    resolved_model_path = _resolve_path(model_path, "") if model_path else None

    default_account = AccountConfig(
        name="default",
        credentials_file=credentials_file,
        token_file=token_file,
        user_id=os.getenv("GMAIL_USER_ID", "me"),
    )
    accounts: Dict[str, AccountConfig] = {default_account.name: default_account}

    if accounts_file.exists():
        data = json.loads(accounts_file.read_text(encoding="utf-8"))
        for item in data.get("accounts", []):
            name = item.get("name")
            if not name:
                continue
            accounts[name] = AccountConfig(
                name=name,
                credentials_file=_resolve_path(item.get("credentials_file"), "credentials.json"),
                token_file=_resolve_path(item.get("token_file"), "token.json"),
                user_id=item.get("user_id", "me"),
            )

    return AppConfig(
        rules_file=rules_file,
        log_dir=log_dir,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        fetch_batch_size=fetch_batch_size,
        stats_file=stats_file,
        model_path=resolved_model_path,
        transformer_model=os.getenv("TRANSFORMER_MODEL_NAME"),
        db_path=db_path,
        accounts=accounts,
        default_account=default_account,
        accounts_file=accounts_file,
    )
