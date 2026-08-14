# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


@frappe.whitelist()
def list_conversations(channel: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
	filters: dict = {}
	if channel:
		filters["channel"] = channel
	if status:
		filters["status"] = status
	return frappe.get_list(
		"Conversation",
		filters=filters,
		fields=[
			"name",
			"channel",
			"provider",
			"account",
			"party_type",
			"party",
			"assigned_to",
			"status",
			"last_message",
			"last_message_time",
			"unread_count",
			"conversation_type",
		],
		order_by="last_message_time desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def list_messages(conversation: str, limit: int = 100) -> list[dict]:
	frappe.get_doc("Conversation", conversation).check_permission("read")
	return frappe.get_all(
		"Message",
		filters={"conversation": conversation},
		fields=[
			"name",
			"direction",
			"sender",
			"recipient",
			"message",
			"message_type",
			"status",
			"sent_at",
			"creation",
			"reference_doctype",
			"reference_name",
		],
		order_by="creation asc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def mark_read(conversation: str) -> None:
	doc = frappe.get_doc("Conversation", conversation)
	doc.check_permission("write")
	doc.db_set("unread_count", 0)
