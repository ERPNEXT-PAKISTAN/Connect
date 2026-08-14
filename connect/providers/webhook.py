# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

from connect.providers.base import MessagingProvider
from connect.providers.http import record_account_status, request_json, safe_password
from connect.providers.types import IncomingMessage, ProviderStatus, SendResult


class WebhookProvider(MessagingProvider):
	channel = "Webhook"
	provider_key = "Webhook"
	kind = "builtin"

	def get_status(self) -> ProviderStatus:
		url = (self.account.get("webhook_url") if self.account else None) or ""
		return self._base_status(configured=bool(url), detail="Generic HTTP webhook")

	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		self._require_enabled()
		url = (self.account.get("webhook_url") if self.account else None) or kwargs.get("url")
		self._require_configured(url)
		headers = {"Content-Type": "application/json"}
		token = safe_password(self.account, "webhook_bearer_token")
		if token:
			headers["Authorization"] = f"Bearer {token}"
		timeout = int(self.account.get("webhook_timeout") or 15) if self.account else 15
		body = request_json(
			"POST",
			url,
			json={"recipient": recipient, "text": text, "metadata": kwargs.get("metadata") or {}},
			headers=headers,
			timeout=timeout,
		)
		record_account_status(self.account, True)
		return SendResult(ok=True, raw=body or {})

	def handle_webhook(self, payload, headers=None) -> IncomingMessage | None:
		payload = payload or {}
		return IncomingMessage(
			channel="Webhook",
			provider="Webhook",
			sender=str(payload.get("sender") or ""),
			recipient=str(payload.get("recipient") or ""),
			text=str(payload.get("text") or payload.get("message") or ""),
			external_id=str(payload.get("id") or ""),
			metadata={"payload": payload},
		)
