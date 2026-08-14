# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import now_datetime

from connect.queue.jobs import enqueue_message


@frappe.whitelist()
def send_message(
	channel: str,
	recipient: str,
	message: str,
	account: str | None = None,
	template: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	print_format: str | None = None,
	attach_pdf: int | str | None = 0,
	conversation: str | None = None,
	provider: str | None = None,
) -> dict:
	frappe.only_for(("System Manager", "Connect Manager", "Connect User"))
	attach_pdf = int(attach_pdf or 0)

	if not account:
		account = frappe.db.get_value(
			"Channel Account",
			{"channel": channel, "enabled": 1, "is_default": 1},
			"name",
		) or frappe.db.get_value("Channel Account", {"channel": channel, "enabled": 1}, "name")

	if account and not provider:
		provider = frappe.db.get_value("Channel Account", account, "provider")

	if template:
		tpl = frappe.get_doc("Message Template", template)
		if not message:
			ctx = {}
			if reference_doctype and reference_name:
				ctx["doc"] = frappe.get_doc(reference_doctype, reference_name)
			message = frappe.render_template(tpl.body or "", ctx)
		print_format = print_format or tpl.print_format
		if tpl.attach_pdf:
			attach_pdf = 1

	if not conversation and channel == "Internal":
		from connect.chat import ensure_internal_conversation

		conversation = ensure_internal_conversation(frappe.session.user, recipient)

	if not conversation:
		conversation = _find_or_create_conversation(channel, account, recipient, provider)

	msg = frappe.get_doc(
		{
			"doctype": "Message",
			"conversation": conversation,
			"direction": "Internal" if channel == "Internal" else "Outgoing",
			"channel": channel,
			"provider": provider,
			"account": account,
			"sender": frappe.session.user,
			"recipient": recipient,
			"message": message,
			"message_type": "PDF" if attach_pdf else "Text",
			"status": "Queued" if channel != "Internal" else "Sent",
			"sent_at": now_datetime() if channel == "Internal" else None,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	)
	msg.insert(ignore_permissions=True)

	if attach_pdf and reference_doctype and reference_name:
		from connect.pdf import attach_pdf_to_message

		attach_pdf_to_message(msg, reference_doctype, reference_name, print_format=print_format)
		msg.save(ignore_permissions=True)

	if channel == "Internal":
		from connect.chat import post_internal_message

		# Message already inserted; publish realtime.
		frappe.publish_realtime(
			"connect:message",
			{"conversation": conversation, "message": msg.name, "text": message, "sender": frappe.session.user},
			user=recipient,
		)
	else:
		enqueue_message(msg.name)

	return {"message": msg.name, "conversation": conversation, "status": msg.status}


def _find_or_create_conversation(channel, account, recipient, provider) -> str:
	existing = frappe.db.get_value(
		"Conversation",
		{"channel": channel, "account": account or "", "contact_identifier": recipient},
		"name",
	)
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "Conversation",
			"conversation_type": "External",
			"channel": channel,
			"provider": provider,
			"account": account,
			"contact_identifier": recipient,
			"status": "Open",
			"unread_count": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name
