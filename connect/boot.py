# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Boot session extras for Desk (Send Message enabled DocTypes)."""

from __future__ import annotations

import frappe


def boot_session(bootinfo) -> None:
	try:
		settings = frappe.get_single("Connect Settings")
	except Exception:
		return

	bootinfo.connect = {
		"enable_send_message_button": bool(settings.enable_send_message_button),
		"enable_internal_chat": bool(settings.enable_internal_chat),
		"enabled_doctypes": [
			row.document_type
			for row in (settings.get("enabled_doctypes") or [])
			if row.enabled and row.document_type
		],
	}
