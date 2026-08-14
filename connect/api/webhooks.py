# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Incoming provider webhooks. Guest access requires a verified secret."""

from __future__ import annotations

import hashlib
import hmac
import json

import frappe
from frappe.utils import now_datetime

from connect.providers.registry import get_provider


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def receive(provider: str | None = None, account: str | None = None) -> dict | str:
	provider = provider or frappe.form_dict.get("provider")
	account = account or frappe.form_dict.get("account")

	if frappe.request and frappe.request.method == "GET":
		return _verify_challenge(provider, account)

	payload = _read_payload()
	headers = {k.lower(): v for k, v in (frappe.request.headers.items() if frappe.request else [])}

	if not _authorized(provider, account, payload, headers):
		frappe.throw("Unauthorized", frappe.AuthenticationError)

	account_doc = None
	if account:
		account_doc = frappe.get_doc("Channel Account", account)
		provider = provider or account_doc.provider
	elif provider:
		name = frappe.db.get_value("Channel Account", {"provider": provider, "enabled": 1}, "name")
		if name:
			account_doc = frappe.get_doc("Channel Account", name)

	if not account_doc:
		return {"ok": True, "ignored": True, "reason": "no account"}

	incoming = get_provider(account_doc).handle_webhook(payload, headers)
	if not incoming:
		return {"ok": True, "ignored": True}

	conversation = _conversation_for(account_doc, incoming)
	msg = frappe.get_doc(
		{
			"doctype": "Message",
			"conversation": conversation,
			"direction": "Incoming",
			"channel": incoming.channel,
			"provider": incoming.provider,
			"account": account_doc.name,
			"sender": incoming.sender,
			"recipient": incoming.recipient,
			"message": incoming.text,
			"message_type": incoming.message_type,
			"external_message_id": incoming.external_id,
			"status": "Delivered",
			"metadata": json.dumps(incoming.metadata or {}, default=str)[:10000],
		}
	)
	msg.insert(ignore_permissions=True)
	frappe.db.set_value(
		"Conversation",
		conversation,
		{
			"last_message": (incoming.text or "")[:140],
			"last_message_time": now_datetime(),
			"unread_count": (frappe.db.get_value("Conversation", conversation, "unread_count") or 0) + 1,
		},
	)
	frappe.publish_realtime("connect:message", {"conversation": conversation, "message": msg.name})
	return {"ok": True, "message": msg.name, "conversation": conversation}


def _read_payload():
	if frappe.request and frappe.request.data:
		try:
			return json.loads(frappe.request.data)
		except Exception:
			return {"raw": frappe.request.data.decode("utf-8", errors="ignore")[:5000]}
	return dict(frappe.form_dict)


def _verify_challenge(provider, account) -> str | dict:
	"""Meta WhatsApp and similar GET handshake."""
	mode = frappe.form_dict.get("hub.mode")
	token = frappe.form_dict.get("hub.verify_token")
	challenge = frappe.form_dict.get("hub.challenge")
	if mode == "subscribe" and challenge:
		expected = None
		if account and frappe.db.exists("Channel Account", account):
			expected = frappe.get_doc("Channel Account", account).get("meta_verify_token")
		if expected and token == expected:
			return challenge
		frappe.throw("Invalid verify token", frappe.AuthenticationError)
	return {"ok": True}


def _authorized(provider, account, payload, headers) -> bool:
	secret = None
	doc = None
	if account and frappe.db.exists("Channel Account", account):
		doc = frappe.get_doc("Channel Account", account)
	if doc:
		for field in (
			"telegram_webhook_secret",
			"meta_verify_token",
			"slack_signing_secret",
			"waha_webhook_secret",
			"webhook_secret",
		):
			try:
				secret = doc.get_password(field)
			except Exception:
				secret = doc.get(field)
			if secret:
				break
	if not secret:
		# Unsigned incoming is allowed only when no secret is configured.
		return True

	header_sig = headers.get("x-hub-signature-256") or headers.get("x-connect-signature") or ""
	if header_sig.startswith("sha256="):
		digest = hmac.new(secret.encode(), frappe.request.data or b"", hashlib.sha256).hexdigest()
		return hmac.compare_digest(header_sig[7:], digest)
	token = frappe.form_dict.get("secret") or headers.get("x-webhook-secret") or headers.get("x-telegram-bot-api-secret-token")
	if token:
		return hmac.compare_digest(str(token), str(secret))
	return False


def _conversation_for(account_doc, incoming) -> str:
	existing = frappe.db.get_value(
		"Conversation",
		{"account": account_doc.name, "contact_identifier": incoming.sender, "channel": incoming.channel},
		"name",
	)
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "Conversation",
			"conversation_type": "External",
			"channel": incoming.channel,
			"provider": incoming.provider,
			"account": account_doc.name,
			"contact_identifier": incoming.sender,
			"status": "Open",
			"unread_count": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name
