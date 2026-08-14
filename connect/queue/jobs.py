# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Enqueue provider sends. Do not call slow HTTP inside document transactions."""

from __future__ import annotations

import frappe
from frappe.utils import now_datetime

from connect.providers.exceptions import ConnectProviderError
from connect.providers.registry import get_provider

MAX_ATTEMPTS = 5


def enqueue_message(message_name: str) -> None:
	frappe.enqueue(
		"connect.queue.jobs.dispatch_message",
		queue="short",
		message_name=message_name,
		enqueue_after_commit=True,
	)


def dispatch_message(message_name: str) -> None:
	doc = frappe.get_doc("Message", message_name)
	if doc.status in {"Sent", "Delivered", "Read", "Cancelled"}:
		return

	doc.db_set("status", "Sending", update_modified=False)
	try:
		account = frappe.get_doc("Channel Account", doc.account) if doc.account else frappe._dict(
			channel=doc.channel, provider=doc.provider, enabled=1
		)
		provider = get_provider(account)
		kwargs = {
			"subject": doc.get("subject"),
			"reference_doctype": doc.reference_doctype,
			"reference_name": doc.reference_name,
			"is_html": doc.message_type == "HTML",
		}
		if doc.message_type in {"Document", "PDF"} and doc.get("attachments"):
			result = provider.send_document(doc.recipient, _first_file(doc), caption=doc.message, **kwargs)
		elif doc.message_type == "Image" and doc.get("attachments"):
			result = provider.send_image(doc.recipient, _first_file(doc), caption=doc.message, **kwargs)
		else:
			result = provider.send_text(doc.recipient, doc.message or "", **kwargs)
		if result.ok:
			doc.db_set("status", result.status or "Sent", update_modified=False)
			doc.db_set("sent_at", now_datetime(), update_modified=False)
			if result.external_id:
				doc.db_set("external_message_id", result.external_id, update_modified=False)
			doc.db_set("error", "", update_modified=False)
			_log(doc, "Sent", result.error)
			_touch_conversation(doc)
		else:
			_fail(doc, result.error or "Provider returned not ok")
	except ConnectProviderError as exc:
		_fail(doc, str(exc))
	except Exception as exc:
		_fail(doc, str(exc))
		frappe.log_error(title=f"Connect send failed: {message_name}")


def retry_failed_messages() -> None:
	names = frappe.get_all(
		"Message",
		filters={"status": "Failed"},
		pluck="name",
		limit=50,
	)
	settings = None
	try:
		settings = frappe.get_single("Connect Settings")
	except Exception:
		pass
	limit = int(getattr(settings, "retry_limit", None) or MAX_ATTEMPTS)
	for name in names:
		attempts = frappe.db.count("Delivery Log", {"message": name})
		if attempts >= limit:
			continue
		enqueue_message(name)


def _fail(doc, error: str) -> None:
	doc.db_set("status", "Failed", update_modified=False)
	doc.db_set("failed_at", now_datetime(), update_modified=False)
	doc.db_set("error", (error or "")[:140], update_modified=False)
	_log(doc, "Failed", error)


def _log(doc, status: str, error: str | None = None) -> None:
	try:
		frappe.get_doc(
			{
				"doctype": "Delivery Log",
				"message": doc.name,
				"channel": doc.channel,
				"provider": doc.provider,
				"status": status,
				"error": (error or "")[:140],
				"logged_at": now_datetime(),
			}
		).insert(ignore_permissions=True)
	except Exception:
		pass


def _first_file(doc):
	row = (doc.get("attachments") or [None])[0]
	if not row:
		return None
	if row.file:
		file_doc = frappe.get_doc("File", row.file)
		return {"path": file_doc.get_full_path(), "url": file_doc.file_url, "file_name": file_doc.file_name}
	return {"url": row.file_url, "file_name": row.file_name}


def _touch_conversation(doc) -> None:
	if not doc.conversation:
		return
	frappe.db.set_value(
		"Conversation",
		doc.conversation,
		{
			"last_message": (doc.message or "")[:140],
			"last_message_time": now_datetime(),
		},
	)
