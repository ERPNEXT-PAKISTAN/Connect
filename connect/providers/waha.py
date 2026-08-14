# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""WAHA is an external HTTP service. Connect does not embed or install it."""

from __future__ import annotations

from connect.providers.base import MessagingProvider
from connect.providers.http import record_account_status, request_json, safe_password
from connect.providers.types import IncomingMessage, ProviderStatus, SendResult


class WahaProvider(MessagingProvider):
	channel = "WhatsApp"
	provider_key = "WAHA"
	kind = "external"

	def _base_url(self) -> str:
		if self.connector:
			return (self.connector.get("base_url") or "").rstrip("/")
		return (self.account.get("waha_base_url") if self.account else "") or ""

	def _api_key(self) -> str:
		if self.connector:
			return safe_password(self.connector, "api_key")
		return safe_password(self.account, "waha_api_key")

	def _session(self) -> str:
		return (
			(self.account.get("waha_session") if self.account else None)
			or (self.connector.get("default_session") if self.connector else None)
			or "default"
		)

	def _timeout(self) -> int:
		if self.connector and self.connector.get("timeout"):
			return int(self.connector.timeout)
		return int((self.account.get("waha_timeout") if self.account else None) or 20)

	def _verify(self) -> bool:
		if self.connector:
			return bool(self.connector.get("verify_ssl", 1))
		return True

	def _headers(self) -> dict:
		key = self._api_key()
		return {"X-Api-Key": key, "Content-Type": "application/json"} if key else {"Content-Type": "application/json"}

	def get_status(self) -> ProviderStatus:
		url = self._base_url()
		status = self._base_status(configured=bool(url), installed=bool(url), detail="External WAHA HTTP API")
		status.kind = "external"
		return status

	def test_connection(self) -> ProviderStatus:
		status = self.get_status()
		url = self._base_url()
		if not url:
			return status
		try:
			request_json(
				"GET",
				f"{url}/api/sessions",
				headers=self._headers(),
				timeout=self._timeout(),
				verify=self._verify(),
			)
			status.connected = True
			status.installed = True
			record_account_status(self.account, True)
		except Exception as exc:
			status.connected = False
			status.last_error = str(exc)[:140]
			record_account_status(self.account, False, str(exc))
		return status

	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		self._require_enabled()
		url = self._base_url()
		self._require_configured(url)
		self.validate_recipient(recipient)
		body = request_json(
			"POST",
			f"{url}/api/sendText",
			headers=self._headers(),
			json={"session": self._session(), "chatId": _wa_chat_id(recipient), "text": text},
			timeout=self._timeout(),
			verify=self._verify(),
		)
		record_account_status(self.account, True)
		return SendResult(ok=True, external_id=str(body.get("id") or ""), raw=body)

	def send_document(self, recipient: str, file, caption: str | None = None, **kwargs) -> SendResult:
		return self._send_media(recipient, file, caption, "sendFile")

	def send_image(self, recipient: str, file, caption: str | None = None, **kwargs) -> SendResult:
		return self._send_media(recipient, file, caption, "sendImage")

	def _send_media(self, recipient, file, caption, method) -> SendResult:
		self._require_enabled()
		url = self._base_url()
		self._require_configured(url)
		path = file if isinstance(file, str) else (file.get("url") or file.get("path") if isinstance(file, dict) else None)
		body = request_json(
			"POST",
			f"{url}/api/{method}",
			headers=self._headers(),
			json={
				"session": self._session(),
				"chatId": _wa_chat_id(recipient),
				"file": {"url": path} if path and str(path).startswith("http") else {"path": path},
				"caption": caption or "",
			},
			timeout=self._timeout(),
			verify=self._verify(),
		)
		return SendResult(ok=True, raw=body)

	def handle_webhook(self, payload, headers=None) -> IncomingMessage | None:
		payload = payload or {}
		event = payload.get("event") or payload.get("type") or ""
		data = payload.get("payload") or payload.get("data") or payload
		if "message" not in event.lower() and not data.get("body") and not data.get("from"):
			if not data.get("from"):
				return None
		return IncomingMessage(
			channel="WhatsApp",
			provider="WAHA",
			sender=str(data.get("from") or ""),
			text=str(data.get("body") or data.get("text") or ""),
			external_id=str(data.get("id") or ""),
			metadata={"payload": payload},
		)


def _wa_chat_id(recipient: str) -> str:
	value = (recipient or "").strip()
	if "@" in value:
		return value
	digits = "".join(ch for ch in value if ch.isdigit())
	return f"{digits}@c.us" if digits else value
