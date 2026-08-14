# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

from connect.providers.base import MessagingProvider
from connect.providers.http import record_account_status, request_json, safe_password
from connect.providers.types import IncomingMessage, ProviderStatus, SendResult


class MetaWhatsAppProvider(MessagingProvider):
	channel = "WhatsApp"
	provider_key = "Meta Cloud API"
	kind = "builtin"

	def _token(self) -> str:
		return safe_password(self.account, "meta_access_token")

	def _version(self) -> str:
		return (self.account.get("meta_api_version") if self.account else None) or "v21.0"

	def _phone_id(self) -> str:
		return (self.account.get("meta_phone_number_id") if self.account else None) or ""

	def get_status(self) -> ProviderStatus:
		configured = bool(self._token() and self._phone_id())
		return self._base_status(configured=configured, detail="Meta WhatsApp Cloud API")

	def test_connection(self) -> ProviderStatus:
		status = self.get_status()
		token, phone_id = self._token(), self._phone_id()
		if not (token and phone_id):
			return status
		try:
			request_json(
				"GET",
				f"https://graph.facebook.com/{self._version()}/{phone_id}",
				headers={"Authorization": f"Bearer {token}"},
				timeout=15,
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
		token, phone_id = self._token(), self._phone_id()
		self._require_configured(token, phone_id)
		self.validate_recipient(recipient)
		body = request_json(
			"POST",
			f"https://graph.facebook.com/{self._version()}/{phone_id}/messages",
			headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
			json={
				"messaging_product": "whatsapp",
				"to": recipient.replace("+", "").replace(" ", ""),
				"type": "text",
				"text": {"body": text},
			},
			timeout=20,
		)
		msg_id = ""
		messages = body.get("messages") or []
		if messages:
			msg_id = str(messages[0].get("id") or "")
		record_account_status(self.account, True)
		return SendResult(ok=True, external_id=msg_id, raw=body)

	def handle_webhook(self, payload, headers=None) -> IncomingMessage | None:
		try:
			entry = (payload or {}).get("entry") or []
			changes = (entry[0].get("changes") if entry else []) or []
			value = (changes[0].get("value") if changes else {}) or {}
			messages = value.get("messages") or []
			if not messages:
				return None
			msg = messages[0]
			text = ((msg.get("text") or {}).get("body")) or ""
			return IncomingMessage(
				channel="WhatsApp",
				provider="Meta Cloud API",
				sender=str(msg.get("from") or ""),
				text=text,
				message_type=str(msg.get("type") or "Text").title(),
				external_id=str(msg.get("id") or ""),
				metadata={"payload": payload},
			)
		except Exception:
			return None
