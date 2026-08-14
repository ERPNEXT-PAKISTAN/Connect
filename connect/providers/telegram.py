# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

from connect.providers.base import MessagingProvider
from connect.providers.http import record_account_status, request_json, safe_password
from connect.providers.types import IncomingMessage, ProviderStatus, SendResult


class TelegramProvider(MessagingProvider):
	channel = "Telegram"
	provider_key = "Telegram"
	kind = "builtin"

	def _token(self) -> str:
		return safe_password(self.account, "telegram_bot_token")

	def get_status(self) -> ProviderStatus:
		token = self._token()
		status = self._base_status(configured=bool(token), detail="Telegram Bot API")
		return status

	def test_connection(self) -> ProviderStatus:
		token = self._token()
		status = self.get_status()
		if not token:
			return status
		try:
			me = request_json("GET", f"https://api.telegram.org/bot{token}/getMe", timeout=15)
			status.connected = bool(me.get("ok"))
			status.detail = (me.get("result") or {}).get("username") or status.detail
			record_account_status(self.account, status.connected)
		except Exception as exc:
			status.connected = False
			status.last_error = str(exc)[:140]
			record_account_status(self.account, False, str(exc))
		return status

	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		self._require_enabled()
		token = self._token()
		self._require_configured(token)
		self.validate_recipient(recipient)
		chat_id = recipient or (self.account.get("telegram_default_chat") if self.account else None)
		body = request_json(
			"POST",
			f"https://api.telegram.org/bot{token}/sendMessage",
			json={"chat_id": chat_id, "text": text},
			timeout=20,
		)
		ok = bool(body.get("ok"))
		record_account_status(self.account, ok, None if ok else str(body))
		result = body.get("result") or {}
		return SendResult(ok=ok, external_id=str(result.get("message_id") or ""), raw=body)

	def send_document(self, recipient: str, file, caption: str | None = None, **kwargs) -> SendResult:
		return self._send_file(recipient, file, caption, "sendDocument", "document")

	def send_image(self, recipient: str, file, caption: str | None = None, **kwargs) -> SendResult:
		return self._send_file(recipient, file, caption, "sendPhoto", "photo")

	def _send_file(self, recipient, file, caption, method, field) -> SendResult:
		self._require_enabled()
		token = self._token()
		self._require_configured(token)
		self.validate_recipient(recipient)
		path = file if isinstance(file, str) else (file.get("path") if isinstance(file, dict) else None)
		if not path:
			return self.send_text(recipient, caption or "")
		with open(path, "rb") as handle:
			body = request_json(
				"POST",
				f"https://api.telegram.org/bot{token}/{method}",
				data={"chat_id": recipient, "caption": caption or ""},
				files={field: handle},
				timeout=60,
			)
		ok = bool(body.get("ok"))
		record_account_status(self.account, ok)
		result = body.get("result") or {}
		return SendResult(ok=ok, external_id=str(result.get("message_id") or ""), raw=body)

	def handle_webhook(self, payload, headers=None) -> IncomingMessage | None:
		message = (payload or {}).get("message") or (payload or {}).get("edited_message") or {}
		if not message:
			return None
		chat = message.get("chat") or {}
		frm = message.get("from") or {}
		text = message.get("text") or message.get("caption") or ""
		return IncomingMessage(
			channel="Telegram",
			provider="Telegram",
			sender=str(frm.get("id") or chat.get("id") or ""),
			recipient=str(chat.get("id") or ""),
			text=text,
			external_id=str(message.get("message_id") or ""),
			metadata={"update": payload},
		)
