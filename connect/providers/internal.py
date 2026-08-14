# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

from connect.providers.base import MessagingProvider
from connect.providers.exceptions import ProviderUnavailable
from connect.providers.http import record_account_status
from connect.providers.types import SendResult


class InternalProvider(MessagingProvider):
	channel = "Internal"
	provider_key = "Internal"
	kind = "builtin"

	def get_status(self):
		status = self._base_status(configured=True, connected=True, detail="Frappe users")
		status.enabled = True
		status.installed = True
		return status

	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		self.validate_recipient(recipient)
		import frappe

		if not frappe.db.exists("User", recipient):
			raise ProviderUnavailable(f"User {recipient} does not exist")
		record_account_status(self.account, True)
		return SendResult(ok=True, status="Sent", raw={"recipient": recipient})
