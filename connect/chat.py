# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Internal Chat — Frappe users only. No external provider."""

from __future__ import annotations

import frappe
from frappe.utils import now_datetime


def ensure_internal_conversation(user: str, other: str) -> str:
	existing = frappe.db.get_value(
		"Conversation",
		{
			"conversation_type": "Internal",
			"channel": "Internal",
			"party": other if frappe.session.user == user else user,
			"assigned_to": user if frappe.session.user == user else other,
		},
		"name",
	)
	if existing:
		return existing

	# Match either orientation of the pair.
	name = frappe.db.sql(
		"""
		select name from `tabConversation`
		where conversation_type = 'Internal' and channel = 'Internal'
			and (
				(party = %(a)s and assigned_to = %(b)s)
				or (party = %(b)s and assigned_to = %(a)s)
			)
		limit 1
		""",
		{"a": user, "b": other},
	)
	if name:
		return name[0][0]

	doc = frappe.get_doc(
		{
			"doctype": "Conversation",
			"conversation_type": "Internal",
			"channel": "Internal",
			"provider": "Internal",
			"party_type": "User",
			"party": other,
			"assigned_to": user,
			"status": "Open",
			"unread_count": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def post_internal_message(
	conversation: str,
	text: str,
	*,
	attachments: list | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> str:
	conv = frappe.get_doc("Conversation", conversation)
	if conv.conversation_type != "Internal":
		frappe.throw("Not an internal conversation")

	recipient = conv.party if conv.assigned_to == frappe.session.user else conv.assigned_to
	msg = frappe.get_doc(
		{
			"doctype": "Message",
			"conversation": conv.name,
			"direction": "Internal",
			"channel": "Internal",
			"provider": "Internal",
			"sender": frappe.session.user,
			"recipient": recipient,
			"message": text,
			"message_type": "Text",
			"status": "Sent",
			"sent_at": now_datetime(),
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	)
	for att in attachments or []:
		msg.append("attachments", att)
	msg.insert(ignore_permissions=True)

	unread = (conv.unread_count or 0) + 1
	conv.db_set("last_message", (text or "")[:140], update_modified=False)
	conv.db_set("last_message_time", now_datetime(), update_modified=False)
	conv.db_set("unread_count", unread, update_modified=False)

	frappe.publish_realtime(
		"connect:message",
		{"conversation": conv.name, "message": msg.name, "text": text, "sender": frappe.session.user},
		user=recipient,
	)
	return msg.name
