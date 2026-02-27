from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from utils.config import AccountConfig

LOGGER = logging.getLogger(__name__)
SCOPES: Iterable[str] = ("https://www.googleapis.com/auth/gmail.modify",)


class AuthService:
    """Handle OAuth2 credential lifecycle for a specific Gmail account."""

    def __init__(self, account: AccountConfig):
        self._account = account

    def _save_credentials(self, creds: Credentials) -> None:
        LOGGER.debug("Persisting OAuth tokens to %s", self._account.token_file)
        self._account.token_file.write_text(creds.to_json(), encoding="utf-8")

    def _load_existing_credentials(self) -> Credentials | None:
        token_path: Path = self._account.token_file
        if token_path.exists():
            LOGGER.debug("Loading cached credential from %s", token_path)
            data = token_path.read_text(encoding="utf-8")
            return Credentials.from_authorized_user_info(json.loads(data), SCOPES)
        return None

    def authenticate(self) -> Credentials:
        creds = self._load_existing_credentials()
        if creds and creds.expired and creds.refresh_token:
            LOGGER.info("Refreshing expired Gmail token")
            creds.refresh(Request())
            self._save_credentials(creds)
            return creds

        if creds and creds.valid:
            return creds

        LOGGER.info("Initiating OAuth flow using %s", self._account.credentials_file)
        flow = InstalledAppFlow.from_client_secrets_file(str(self._account.credentials_file), scopes=SCOPES)
        creds = flow.run_local_server(port=0)
        self._save_credentials(creds)
        return creds
