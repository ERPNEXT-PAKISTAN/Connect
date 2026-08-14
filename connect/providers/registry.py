# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Map (channel, provider) → implementation. Business code uses this, not vendor modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

from connect.providers.exceptions import ProviderDisabled, ProviderNotConfigured

if TYPE_CHECKING:
	from connect.providers.base import MessagingProvider

CHANNEL_PROVIDERS: dict[str, list[str]] = {
	"WhatsApp": ["WAHA", "WhatsApp Web.js", "Meta Cloud API"],
	"Telegram": ["Telegram"],
	"Firebase": ["Firebase"],
	"Slack": ["Slack"],
	"Discord": ["Discord"],
	"Email": ["Email"],
	"Webhook": ["Webhook"],
	"Internal": ["Internal"],
	"Frappe-Connect": ["Frappe-Connect"],
}

BUILTIN_PROVIDERS = {
	"Telegram",
	"Firebase",
	"Slack",
	"Discord",
	"Meta Cloud API",
	"Email",
	"Webhook",
	"Internal",
}

EXTERNAL_CONNECTOR_TYPES = {
	"WAHA",
	"WhatsApp Web.js",
	"n8n",
	"Ollama",
	"OCR",
	"Frappe-Connect",
}


def get_provider(account=None, *, channel: str | None = None, provider_key: str | None = None) -> MessagingProvider:
	if account is None:
		if not channel or not provider_key:
			raise ProviderNotConfigured("Channel and provider are required")
		account = frappe._dict(channel=channel, provider=provider_key, enabled=1)

	channel = account.get("channel") or channel
	provider_key = account.get("provider") or provider_key
	connector = None
	if account.get("external_connector"):
		try:
			connector = frappe.get_doc("External Connector", account.external_connector)
		except Exception:
			connector = None

	cls = _class_for(provider_key)
	provider = cls(account=account, connector=connector)
	return provider


def _class_for(provider_key: str):
	from connect.providers.discord import DiscordProvider
	from connect.providers.email_provider import EmailProvider
	from connect.providers.firebase import FirebaseProvider
	from connect.providers.frappe_connect_gateway import FrappeConnectGatewayProvider
	from connect.providers.internal import InternalProvider
	from connect.providers.meta_whatsapp import MetaWhatsAppProvider
	from connect.providers.slack import SlackProvider
	from connect.providers.telegram import TelegramProvider
	from connect.providers.waha import WahaProvider
	from connect.providers.webhook import WebhookProvider
	from connect.providers.whatsapp_webjs import WhatsAppWebJSProvider

	mapping = {
		"Telegram": TelegramProvider,
		"Firebase": FirebaseProvider,
		"Slack": SlackProvider,
		"Discord": DiscordProvider,
		"Meta Cloud API": MetaWhatsAppProvider,
		"Email": EmailProvider,
		"Webhook": WebhookProvider,
		"Internal": InternalProvider,
		"WAHA": WahaProvider,
		"WhatsApp Web.js": WhatsAppWebJSProvider,
		"Frappe-Connect": FrappeConnectGatewayProvider,
	}
	if provider_key not in mapping:
		raise ProviderDisabled(f"Unknown provider: {provider_key}")
	return mapping[provider_key]
