from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(slots=True)
class AppConfig:
    credentials_file: Path
    token_file: Path
    user_id: str
    rules_file: Path
    log_dir: Path
    log_level: str
    fetch_batch_size: int
    stats_file: Path
    model_path: Optional[Path]
    transformer_model: Optional[str]


def _resolve_path(value: str | None, fallback: str) -> Path:
    candidate = Path(value or fallback)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate


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

    log_dir.mkdir(parents=True, exist_ok=True)
    stats_file.parent.mkdir(parents=True, exist_ok=True)

    fetch_batch_size = int(os.getenv("FETCH_BATCH_SIZE", "25"))

    model_path = os.getenv("ML_MODEL_PATH")
    resolved_model_path = _resolve_path(model_path, "") if model_path else None

    return AppConfig(
        credentials_file=credentials_file,
        token_file=token_file,
        user_id=os.getenv("GMAIL_USER_ID", "me"),
        rules_file=rules_file,
        log_dir=log_dir,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        fetch_batch_size=fetch_batch_size,
        stats_file=stats_file,
        model_path=resolved_model_path,
        transformer_model=os.getenv("TRANSFORMER_MODEL_NAME"),
    )
