# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Optional standalone Frappe-Connect gateway. Connect does not require it."""

from __future__ import annotations

from connect.providers.base import MessagingProvider
from connect.providers.http import record_account_status, request_json, safe_password
from connect.providers.types import IncomingMessage, ProviderStatus, SendResult


class FrappeConnectGatewayProvider(MessagingProvider):
	channel = "Frappe-Connect"
	provider_key = "Frappe-Connect"
	kind = "external"

	def _url(self) -> str:
		if self.connector:
			return (self.connector.get("base_url") or "").rstrip("/")
		return ""

	def get_status(self) -> ProviderStatus:
		url = self._url()
		return self._base_status(configured=bool(url), installed=bool(url), detail="Optional standalone gateway")

	def test_connection(self) -> ProviderStatus:
		status = self.get_status()
		url = self._url()
		if not url:
			return status
		try:
			request_json("GET", f"{url}/api/v1/health", timeout=int(self.connector.get("timeout") or 15))
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
		key = safe_password(self.connector, "api_key")
		body = request_json(
			"POST",
			f"{url}/api/v1/messages",
			headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
			json={"recipient": recipient, "text": text, "channel": kwargs.get("channel")},
			timeout=int(self.connector.get("timeout") or 20),
		)
		return SendResult(ok=True, raw=body or {})

	def handle_webhook(self, payload, headers=None) -> IncomingMessage | None:
		payload = payload or {}
		return IncomingMessage(
			channel=str(payload.get("channel") or "Frappe-Connect"),
			provider="Frappe-Connect",
			sender=str(payload.get("sender") or ""),
			recipient=str(payload.get("recipient") or ""),
			text=str(payload.get("text") or ""),
			external_id=str(payload.get("id") or ""),
			metadata={"payload": payload},
		)
