# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

from connect.providers.base import MessagingProvider
from connect.providers.http import record_account_status, request_json, safe_password
from connect.providers.types import IncomingMessage, ProviderStatus, SendResult


class DiscordProvider(MessagingProvider):
	channel = "Discord"
	provider_key = "Discord"
	kind = "builtin"

	def get_status(self) -> ProviderStatus:
		mode = (self.account.get("discord_mode") if self.account else None) or "Webhook"
		configured = bool(
			safe_password(self.account, "discord_webhook_url")
			or safe_password(self.account, "discord_bot_token")
		)
		return self._base_status(configured=configured, detail=f"Discord {mode}")

	def test_connection(self) -> ProviderStatus:
		status = self.get_status()
		url = safe_password(self.account, "discord_webhook_url")
		try:
			if url:
				request_json("POST", url, json={"content": "Connect connection test"}, timeout=15)
				status.connected = True
				record_account_status(self.account, True)
			else:
				status.detail = "Configure webhook URL or bot token"
		except Exception as exc:
			status.connected = False
			status.last_error = str(exc)[:140]
			record_account_status(self.account, False, str(exc))
		return status

	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		self._require_enabled()
		url = safe_password(self.account, "discord_webhook_url")
		self._require_configured(url)
		body = request_json("POST", url, json={"content": text}, timeout=20)
		record_account_status(self.account, True)
		return SendResult(ok=True, raw=body or {})

	def handle_webhook(self, payload, headers=None) -> IncomingMessage | None:
		if not payload:
			return None
		return IncomingMessage(
			channel="Discord",
			provider="Discord",
			sender=str((payload.get("author") or {}).get("id") or ""),
			text=str(payload.get("content") or ""),
			external_id=str(payload.get("id") or ""),
			metadata={"payload": payload},
		)
