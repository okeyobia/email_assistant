from __future__ import annotations

import base64
import logging
from email.utils import parsedate_to_datetime
from typing import Dict, List, Sequence

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.email_message import EmailMessage
from services.auth_service import AuthService
from utils.config import AppConfig

LOGGER = logging.getLogger(__name__)


class GmailService:
    """Wrapper around the Gmail API for the operations we need."""

    def __init__(self, config: AppConfig, auth_service: AuthService):
        self._config = config
        self._auth_service = auth_service
        creds = self._auth_service.authenticate()
        self._client = build("gmail", "v1", credentials=creds, cache_discovery=False)

    @property
    def user_id(self) -> str:
        return self._config.user_id

    def fetch_unread_messages(self, max_results: int) -> List[EmailMessage]:
        try:
            response = (
                self._client.users()
                .messages()
                .list(userId=self.user_id, labelIds=["UNREAD"], maxResults=max_results)
                .execute()
            )
        except HttpError as exc:
            LOGGER.error("Failed to fetch unread messages: %s", exc)
            raise

        messages = response.get("messages", [])
        LOGGER.info("Fetched %s unread message headers", len(messages))
        hydrated: List[EmailMessage] = []
        for message in messages:
            hydrated.append(self._fetch_message(message["id"]))
        return hydrated

    def _fetch_message(self, message_id: str) -> EmailMessage:
        response = (
            self._client.users()
            .messages()
            .get(userId=self.user_id, id=message_id, format="full")
            .execute()
        )
        payload = response.get("payload", {})
        headers = _headers_to_dict(payload.get("headers", []))
        body_text = _extract_body(payload)
        subject = headers.get("subject", "(no subject)")
        snippet = response.get("snippet", "")
        sender = headers.get("from")
        received_at = None
        if date_header := headers.get("date"):
            try:
                received_at = parsedate_to_datetime(date_header)
            except (TypeError, ValueError):
                LOGGER.debug("Unable to parse date header: %s", date_header)
        labels = response.get("labelIds", [])
        return EmailMessage(
            id=response["id"],
            thread_id=response.get("threadId"),
            subject=subject,
            body=body_text,
            snippet=snippet,
            sender=sender,
            labels=labels,
            received_at=received_at,
        )

    def apply_labels(self, message_id: str, labels_to_add: Sequence[str]) -> Dict:
        if not labels_to_add:
            LOGGER.debug("No labels supplied for message %s", message_id)
            return {}
        body = {"addLabelIds": list(labels_to_add)}
        response = (
            self._client.users()
            .messages()
            .modify(userId=self.user_id, id=message_id, body=body)
            .execute()
        )
        LOGGER.info("Applied labels %s to message %s", labels_to_add, message_id)
        return response

    def ensure_label(self, label_name: str) -> str:
        existing = self._list_labels()
        for label in existing:
            if label["name"].lower() == label_name.lower():
                LOGGER.debug("Label %s already exists as %s", label_name, label["id"])
                return label["id"]
        body = {"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
        response = self._client.users().labels().create(userId=self.user_id, body=body).execute()
        LOGGER.info("Created label %s with id %s", label_name, response["id"])
        return response["id"]

    def _list_labels(self) -> List[Dict]:
        response = self._client.users().labels().list(userId=self.user_id).execute()
        return response.get("labels", [])


def _headers_to_dict(headers: Sequence[Dict[str, str]]) -> Dict[str, str]:
    mapped: Dict[str, str] = {}
    for header in headers:
        name = header.get("name", "").lower()
        value = header.get("value", "")
        mapped[name] = value
    return mapped


def _extract_body(payload: Dict) -> str:
    if "body" in payload and payload["body"].get("data"):
        return _decode_base64(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return _decode_base64(data)
        if part.get("parts"):
            nested = _extract_body(part)
            if nested:
                return nested
    return ""


def _decode_base64(data: str) -> str:
    try:
        decoded = base64.urlsafe_b64decode(data).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""
    return decoded
