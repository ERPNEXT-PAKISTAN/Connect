# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Simple Notification Rules. Advanced workflows may call n8n separately."""

from __future__ import annotations

import frappe

from connect.queue.jobs import enqueue_message

SKIP_DOCTYPES = {
	"Message",
	"Conversation",
	"Delivery Log",
	"Notification Rule",
	"Connect Settings",
	"Channel Account",
	"External Connector",
	"Webhook Endpoint",
	"Error Log",
	"Version",
	"Activity Log",
}


def on_submit(doc, method: str | None = None) -> None:
	_dispatch(doc, "on_submit")


def on_cancel(doc, method: str | None = None) -> None:
	_dispatch(doc, "on_cancel")


def on_update(doc, method: str | None = None) -> None:
	_dispatch(doc, "on_update")


def _dispatch(doc, event: str) -> None:
	if doc.doctype in SKIP_DOCTYPES or getattr(doc, "flags", None) and doc.flags.get("connect_skip_rules"):
		return
	if not frappe.db.exists("DocType", "Notification Rule"):
		return

	rules = frappe.get_all(
		"Notification Rule",
		filters={"enabled": 1, "document_type": doc.doctype, "event": event},
		pluck="name",
	)
	for name in rules:
		try:
			_run_rule(frappe.get_doc("Notification Rule", name), doc)
		except Exception:
			frappe.log_error(title=f"Connect rule failed: {name}")


def _run_rule(rule, doc) -> None:
	recipient = _resolve_recipient(rule, doc)
	if not recipient:
		return

	body = rule.message or ""
	if rule.template:
		template = frappe.get_doc("Message Template", rule.template)
		body = frappe.render_template(template.body or body, {"doc": doc})
	else:
		body = frappe.render_template(body, {"doc": doc}) if body else f"{doc.doctype} {doc.name}"

	msg = frappe.get_doc(
		{
			"doctype": "Message",
			"direction": "Outgoing",
			"channel": rule.channel,
			"provider": rule.provider,
			"account": rule.account,
			"sender": frappe.session.user,
			"recipient": recipient,
			"message": body,
			"message_type": "PDF" if rule.attach_pdf else "Text",
			"status": "Queued",
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
		}
	)
	msg.insert(ignore_permissions=True)
	if rule.attach_pdf:
		from connect.pdf import attach_pdf_to_message

		attach_pdf_to_message(
			msg,
			doc.doctype,
			doc.name,
			print_format=rule.print_format,
		)
		msg.save(ignore_permissions=True)
	enqueue_message(msg.name)


def _resolve_recipient(rule, doc) -> str | None:
	source = rule.recipient_source
	if source == "Static":
		return rule.static_recipient
	if source == "Field" and rule.recipient_field:
		return doc.get(rule.recipient_field)
	if source in {"Customer", "Supplier", "Lead", "User"}:
		party = doc.get(source.lower()) or doc.get("party_name")
		if source == "User":
			return party
		return _contact_identifier(party, source, rule.channel)
	if source == "Role" and rule.role:
		users = frappe.get_all("Has Role", filters={"role": rule.role, "parenttype": "User"}, pluck="parent")
		return users[0] if users else None
	return None


def _contact_identifier(party: str | None, party_type: str, channel: str) -> str | None:
	if not party:
		return None
	name = frappe.db.get_value(
		"Messaging Contact",
		{"party_type": party_type, "party": party},
		"name",
	)
	if name:
		ident = frappe.db.get_value(
			"External Identity",
			{"parent": name, "channel": channel, "is_primary": 1},
			"identifier",
		) or frappe.db.get_value("External Identity", {"parent": name, "channel": channel}, "identifier")
		if ident:
			return ident
	if party_type == "Customer":
		return frappe.db.get_value("Customer", party, "mobile_no")
	if party_type == "Supplier":
		return frappe.db.get_value("Supplier", party, "mobile_no")
	if party_type == "Lead":
		return frappe.db.get_value("Lead", party, "mobile_no")
	return None
