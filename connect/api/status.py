# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Overall health stays ok when optional providers fail."""

from __future__ import annotations

import frappe

from connect.providers.registry import CHANNEL_PROVIDERS, get_provider
from connect.providers.status import connector_status


@frappe.whitelist()
def health() -> dict:
	providers = []
	try:
		accounts = frappe.get_all("Channel Account", fields=["name", "channel", "provider", "enabled"])
	except Exception:
		accounts = []

	seen = set()
	for acc in accounts:
		key = (acc.channel, acc.provider)
		seen.add(key)
		try:
			doc = frappe.get_doc("Channel Account", acc.name)
			status = get_provider(doc).get_status().as_dict()
			status["account"] = acc.name
			providers.append(status)
		except Exception as exc:
			providers.append(
				{
					"provider": acc.provider,
					"channel": acc.channel,
					"account": acc.name,
					"installed": True,
					"configured": False,
					"enabled": bool(acc.enabled),
					"connected": False,
					"last_error": str(exc)[:140],
				}
			)

	for channel, keys in CHANNEL_PROVIDERS.items():
		for key in keys:
			if (channel, key) in seen:
				continue
			providers.append(
				{
					"provider": key,
					"channel": channel,
					"kind": "external" if key in {"WAHA", "WhatsApp Web.js", "Frappe-Connect"} else "builtin",
					"installed": True,
					"configured": False,
					"enabled": False,
					"connected": False,
					"detail": "Not configured",
				}
			)

	connectors = []
	try:
		for row in frappe.get_all("External Connector", pluck="name"):
			doc = frappe.get_doc("External Connector", row)
			connectors.append(connector_status(doc).as_dict())
	except Exception:
		pass

	return {
		"ok": True,
		"app": "connect",
		"version": "0.0.1",
		"providers": providers,
		"connectors": connectors,
	}


@frappe.whitelist()
def test_connection(doctype: str, name: str) -> dict:
	frappe.only_for(("System Manager", "Connect Manager"))
	if doctype == "Channel Account":
		doc = frappe.get_doc("Channel Account", name)
		status = get_provider(doc).test_connection()
		return status.as_dict()
	if doctype == "External Connector":
		doc = frappe.get_doc("External Connector", name)
		status = connector_status(doc)
		from frappe.utils import now_datetime

		doc.db_set("connection_status", "Connected" if status.connected else "Error", update_modified=False)
		if status.connected:
			doc.db_set("last_successful_connection", now_datetime(), update_modified=False)
			doc.db_set("last_error", "", update_modified=False)
		else:
			doc.db_set("last_error", status.last_error or "", update_modified=False)
		return status.as_dict()
	frappe.throw("Unsupported doctype")


@frappe.whitelist()
def send_test(account: str, recipient: str, text: str | None = None) -> dict:
	frappe.only_for(("System Manager", "Connect Manager"))
	doc = frappe.get_doc("Channel Account", account)
	result = get_provider(doc).send_test(recipient, text)
	return result.as_dict()
