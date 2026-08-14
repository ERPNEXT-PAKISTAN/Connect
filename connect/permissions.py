# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Permission helpers. Connect User sees assigned / own internal threads."""

from __future__ import annotations

import frappe


def _is_manager() -> bool:
	roles = set(frappe.get_roles())
	return bool(roles.intersection({"System Manager", "Connect Manager", "Administrator"}))


def conversation_query(user: str | None = None) -> str:
	if _is_manager():
		return ""
	user = user or frappe.session.user
	return (
		f"""(`tabConversation`.assigned_to = {frappe.db.escape(user)}
		or `tabConversation`.owner = {frappe.db.escape(user)}
		or (`tabConversation`.conversation_type = 'Internal'
			and `tabConversation`.party = {frappe.db.escape(user)}))"""
	)


def message_query(user: str | None = None) -> str:
	if _is_manager():
		return ""
	user = user or frappe.session.user
	return f"""`tabMessage`.conversation in (
		select name from `tabConversation`
		where assigned_to = {frappe.db.escape(user)}
			or owner = {frappe.db.escape(user)}
			or (conversation_type = 'Internal' and party = {frappe.db.escape(user)})
	)"""


def conversation_has_permission(doc, user: str | None = None, ptype: str | None = None) -> bool:
	if _is_manager():
		return True
	user = user or frappe.session.user
	if doc.assigned_to == user or doc.owner == user:
		return True
	return doc.conversation_type == "Internal" and doc.party == user


def message_has_permission(doc, user: str | None = None, ptype: str | None = None) -> bool:
	if _is_manager():
		return True
	if not doc.conversation:
		return doc.owner == (user or frappe.session.user)
	conv = frappe.get_cached_doc("Conversation", doc.conversation)
	return conversation_has_permission(conv, user, ptype)
