# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

from connect.providers.base import MessagingProvider
from connect.providers.http import record_account_status, request_json, safe_password
from connect.providers.types import IncomingMessage, ProviderStatus, SendResult


class SlackProvider(MessagingProvider):
	channel = "Slack"
	provider_key = "Slack"
	kind = "builtin"

	def get_status(self) -> ProviderStatus:
		mode = (self.account.get("slack_mode") if self.account else None) or "Webhook"
		configured = bool(
			safe_password(self.account, "slack_webhook_url")
			or safe_password(self.account, "slack_bot_token")
		)
		return self._base_status(configured=configured, detail=f"Slack {mode}")

	def test_connection(self) -> ProviderStatus:
		status = self.get_status()
		url = safe_password(self.account, "slack_webhook_url")
		token = safe_password(self.account, "slack_bot_token")
		try:
			if url:
				request_json("POST", url, json={"text": "Connect connection test"}, timeout=15)
				status.connected = True
			elif token:
				request_json(
					"POST",
					"https://slack.com/api/auth.test",
					headers={"Authorization": f"Bearer {token}"},
					timeout=15,
				)
				status.connected = True
			record_account_status(self.account, status.connected)
		except Exception as exc:
			status.connected = False
			status.last_error = str(exc)[:140]
			record_account_status(self.account, False, str(exc))
		return status

	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		self._require_enabled()
		url = safe_password(self.account, "slack_webhook_url")
		token = safe_password(self.account, "slack_bot_token")
		self._require_configured(url or token)
		channel = recipient or (self.account.get("slack_default_channel") if self.account else None)
		if url:
			body = request_json("POST", url, json={"text": text, "channel": channel}, timeout=20)
		else:
			body = request_json(
				"POST",
				"https://slack.com/api/chat.postMessage",
				headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
				json={"channel": channel, "text": text},
				timeout=20,
			)
		ok = body.get("ok", True) is not False
		record_account_status(self.account, ok)
		return SendResult(ok=ok, raw=body, external_id=str((body or {}).get("ts") or ""))

	def handle_webhook(self, payload, headers=None) -> IncomingMessage | None:
		event = (payload or {}).get("event") or payload or {}
		text = event.get("text") or ""
		if not text:
			return None
		return IncomingMessage(
			channel="Slack",
			provider="Slack",
			sender=str(event.get("user") or ""),
			recipient=str(event.get("channel") or ""),
			text=text,
			external_id=str(event.get("ts") or ""),
			metadata={"payload": payload},
		)
