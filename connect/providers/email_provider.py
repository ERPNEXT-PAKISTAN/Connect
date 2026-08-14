# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from connect.providers.base import MessagingProvider
from connect.providers.exceptions import ProviderUnavailable
from connect.providers.http import record_account_status
from connect.providers.types import SendResult


class EmailProvider(MessagingProvider):
	channel = "Email"
	provider_key = "Email"
	kind = "builtin"

	def get_status(self):
		account_name = self.account.get("email_account") if self.account else None
		configured = bool(account_name) or bool(frappe.db.exists("Email Account", {"default_outgoing": 1}))
		status = self._base_status(configured=configured, connected=configured, detail="Frappe Email Account")
		return status

	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		self.validate_recipient(recipient)
		subject = kwargs.get("subject") or "Message from Connect"
		cc = kwargs.get("cc")
		bcc = kwargs.get("bcc")
		attachments = kwargs.get("attachments") or []
		is_html = bool(kwargs.get("is_html"))
		try:
			frappe.sendmail(
				recipients=[recipient],
				cc=cc,
				bcc=bcc,
				subject=subject,
				message=text,
				reference_doctype=kwargs.get("reference_doctype"),
				reference_name=kwargs.get("reference_name"),
				attachments=attachments,
				now=True,
				expose_recipients="header",
				delayed=False,
			)
		except Exception as exc:
			record_account_status(self.account, False, str(exc))
			raise ProviderUnavailable(str(exc)) from exc
		record_account_status(self.account, True)
		return SendResult(ok=True, status="Sent")

	def send_document(self, recipient: str, file, caption: str | None = None, **kwargs) -> SendResult:
		attachments = list(kwargs.get("attachments") or [])
		if file:
			attachments.append(file)
		return self.send_text(recipient, caption or "", attachments=attachments, **kwargs)

	send_image = send_document
