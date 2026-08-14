# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Install defaults for the native Connect app."""

from __future__ import annotations

import frappe
from frappe.permissions import add_permission, update_permission_property

ROLES = ("Connect Manager", "Connect User")

DEFAULT_SEND_DOCTYPES = (
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Delivery Note",
	"Payment Entry",
	"Purchase Order",
	"Purchase Invoice",
	"Customer",
	"Supplier",
	"Lead",
	"Issue",
)


def after_install() -> None:
	_ensure_roles()
	_ensure_settings()
	frappe.clear_cache()


def after_migrate() -> None:
	_ensure_roles()
	_ensure_settings()


def _ensure_roles() -> None:
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			doc = frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1})
			doc.insert(ignore_permissions=True)


def _ensure_settings() -> None:
	if not frappe.db.exists("DocType", "Connect Settings"):
		return

	settings = frappe.get_single("Connect Settings")
	changed = False
	if not settings.enable_internal_chat:
		settings.enable_internal_chat = 1
		changed = True
	if not settings.enable_send_message_button:
		settings.enable_send_message_button = 1
		changed = True
	if not settings.get("enabled_doctypes"):
		for dt in DEFAULT_SEND_DOCTYPES:
			if frappe.db.exists("DocType", dt):
				settings.append("enabled_doctypes", {"document_type": dt, "enabled": 1})
		changed = True
	if changed:
		settings.save(ignore_permissions=True)

	for role in ("System Manager", "Connect Manager"):
		for doctype in (
			"Connect Settings",
			"Channel Account",
			"External Connector",
			"Messaging Contact",
			"Conversation",
			"Message",
			"Message Template",
			"Notification Rule",
			"Delivery Log",
			"Webhook Endpoint",
		):
			if not frappe.db.exists("DocType", doctype):
				continue
			add_permission(doctype, role, 0)
			for perm in ("read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "share", "print", "email"):
				try:
					update_permission_property(doctype, role, 0, perm, 1)
				except Exception:
					pass
