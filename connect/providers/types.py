# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderStatus:
	provider_key: str
	channel: str
	kind: str  # builtin | external
	installed: bool = True
	configured: bool = False
	enabled: bool = False
	connected: bool = False
	last_success: str | None = None
	last_error: str | None = None
	detail: str = ""

	def as_dict(self) -> dict[str, Any]:
		return {
			"provider": self.provider_key,
			"channel": self.channel,
			"kind": self.kind,
			"installed": self.installed,
			"configured": self.configured,
			"enabled": self.enabled,
			"connected": self.connected,
			"last_success": self.last_success,
			"last_error": self.last_error,
			"detail": self.detail,
		}


@dataclass
class SendResult:
	ok: bool
	external_id: str | None = None
	status: str = "Sent"
	error: str | None = None
	raw: dict[str, Any] = field(default_factory=dict)

	def as_dict(self) -> dict[str, Any]:
		return {
			"ok": self.ok,
			"external_id": self.external_id,
			"status": self.status,
			"error": self.error,
			"raw": self.raw,
		}


@dataclass
class IncomingMessage:
	channel: str
	provider: str
	sender: str
	recipient: str = ""
	text: str = ""
	message_type: str = "Text"
	external_id: str = ""
	metadata: dict[str, Any] = field(default_factory=dict)
	attachments: list[dict[str, Any]] = field(default_factory=list)
