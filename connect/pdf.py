# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Frappe print/PDF wrapper. Does not recreate invoice layouts."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils.pdf import get_pdf as frappe_get_pdf


def get_pdf(
	doctype: str,
	name: str,
	print_format: str | None = None,
	language: str | None = None,
	letterhead: str | None = None,
) -> bytes:
	html = frappe.get_print(
		doctype,
		name,
		print_format=print_format,
		letterhead=letterhead,
		no_letterhead=not bool(letterhead),
	)
	if language:
		frappe.local.lang = language
	return frappe_get_pdf(html)


def attach_pdf_to_message(
	message_doc,
	doctype: str,
	name: str,
	print_format: str | None = None,
	language: str | None = None,
	letterhead: str | None = None,
) -> dict[str, Any]:
	pdf = get_pdf(doctype, name, print_format=print_format, language=language, letterhead=letterhead)
	filename = f"{name}.pdf"
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": pdf,
			"is_private": 1,
			"attached_to_doctype": message_doc.doctype,
			"attached_to_name": message_doc.name,
		}
	)
	file_doc.save(ignore_permissions=True)
	message_doc.append(
		"attachments",
		{"file": file_doc.name, "file_url": file_doc.file_url, "file_name": filename},
	)
	return {"file": file_doc.name, "file_url": file_doc.file_url, "file_name": filename}
