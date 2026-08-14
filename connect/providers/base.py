# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from connect.providers.exceptions import InvalidRecipient, ProviderDisabled, ProviderNotConfigured
from connect.providers.types import IncomingMessage, ProviderStatus, SendResult


class MessagingProvider(ABC):
	"""Channel-agnostic provider. Business logic must not parse vendor payloads."""

	channel: str = ""
	provider_key: str = ""
	kind: str = "builtin"  # builtin | external

	def __init__(self, account=None, connector=None):
		self.account = account
		self.connector = connector

	@abstractmethod
	def get_status(self) -> ProviderStatus:
		raise NotImplementedError

	def test_connection(self) -> ProviderStatus:
		status = self.get_status()
		return status

	def send_test(self, recipient: str, text: str | None = None) -> SendResult:
		return self.send_text(recipient, text or "Connect test message")

	@abstractmethod
	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		raise NotImplementedError

	def send_document(self, recipient: str, file, caption: str | None = None, **kwargs) -> SendResult:
		raise ProviderDisabled(f"{self.provider_key} does not send documents")

	def send_image(self, recipient: str, file, caption: str | None = None, **kwargs) -> SendResult:
		raise ProviderDisabled(f"{self.provider_key} does not send images")

	def validate_recipient(self, recipient: str) -> None:
		if not (recipient or "").strip():
			raise InvalidRecipient("Recipient is required")

	def handle_webhook(self, payload: Any, headers: dict | None = None) -> IncomingMessage | None:
		return None

	def _require_enabled(self) -> None:
		if self.account is not None and not self.account.get("enabled"):
			raise ProviderDisabled(f"{self.provider_key} account is disabled")
		if self.connector is not None and not self.connector.get("enabled"):
			raise ProviderDisabled(f"{self.provider_key} connector is disabled")

	def _require_configured(self, *values) -> None:
		if not all(values):
			raise ProviderNotConfigured(f"{self.provider_key} is not configured")

	def _base_status(self, **kwargs) -> ProviderStatus:
		account = self.account
		connector = self.connector
		enabled = bool(account and account.get("enabled"))
		if connector is not None:
			enabled = enabled or bool(connector.get("enabled"))
		return ProviderStatus(
			provider_key=self.provider_key,
			channel=self.channel,
			kind=self.kind,
			installed=True,
			enabled=enabled,
			last_success=account.get("last_successful_connection") if account else None,
			last_error=account.get("last_error") if account else None,
			**kwargs,
		)
