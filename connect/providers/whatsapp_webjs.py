# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""whatsapp-web.js runs as a separate Node service. Not installed into Connect."""

from __future__ import annotations

from connect.providers.base import MessagingProvider
from connect.providers.http import record_account_status, request_json, safe_password
from connect.providers.types import IncomingMessage, ProviderStatus, SendResult


class WhatsAppWebJSProvider(MessagingProvider):
	channel = "WhatsApp"
	provider_key = "WhatsApp Web.js"
	kind = "external"

	def _url(self) -> str:
		if self.connector:
			return (self.connector.get("base_url") or "").rstrip("/")
		return (self.account.get("webjs_service_url") if self.account else "") or ""

	def _key(self) -> str:
		if self.connector:
			return safe_password(self.connector, "api_key")
		return safe_password(self.account, "webjs_api_key")

	def get_status(self) -> ProviderStatus:
		url = self._url()
		return self._base_status(configured=bool(url), installed=bool(url), detail="External whatsapp-web.js HTTP API")

	def test_connection(self) -> ProviderStatus:
		status = self.get_status()
		url = self._url()
		if not url:
			return status
		try:
			request_json(
				"GET",
				f"{url}/health",
				headers={"Authorization": f"Bearer {self._key()}"} if self._key() else None,
				timeout=int((self.connector.get("timeout") if self.connector else 15) or 15),
			)
			status.connected = True
			record_account_status(self.account, True)
		except Exception as exc:
			status.connected = False
			status.last_error = str(exc)[:140]
			record_account_status(self.account, False, str(exc))
		return status

	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		self._require_enabled()
		url = self._url()
		self._require_configured(url)
		self.validate_recipient(recipient)
		body = request_json(
			"POST",
			f"{url}/send",
			headers={"Authorization": f"Bearer {self._key()}", "Content-Type": "application/json"},
			json={"to": recipient, "text": text, "session": (self.account.get("webjs_session") if self.account else None)},
			timeout=20,
		)
		record_account_status(self.account, True)
		return SendResult(ok=True, raw=body or {})

	def handle_webhook(self, payload, headers=None) -> IncomingMessage | None:
		payload = payload or {}
		return IncomingMessage(
			channel="WhatsApp",
			provider="WhatsApp Web.js",
			sender=str(payload.get("from") or ""),
			text=str(payload.get("body") or payload.get("text") or ""),
			external_id=str(payload.get("id") or ""),
			metadata={"payload": payload},
		)
