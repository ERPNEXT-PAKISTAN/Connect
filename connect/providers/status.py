# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Optional external connectors that are not messaging providers."""

from __future__ import annotations

from connect.providers.http import request_json, safe_password
from connect.providers.types import ProviderStatus


def connector_status(connector) -> ProviderStatus:
	kind = connector.get("connector_type") or ""
	url = (connector.get("base_url") or "").rstrip("/")
	enabled = bool(connector.get("enabled"))
	status = ProviderStatus(
		provider_key=kind,
		channel="",
		kind="external",
		installed=bool(url) or kind == "OCR",
		configured=bool(url) if kind != "OCR" else bool(url or connector.get("ocr_mode")),
		enabled=enabled,
		last_success=connector.get("last_successful_connection"),
		last_error=connector.get("last_error"),
		detail=f"External {kind}",
	)
	if not enabled or not url:
		return status
	try:
		if kind == "n8n":
			request_json(
				"GET",
				f"{url}/healthz",
				headers=_auth(connector),
				timeout=int(connector.get("timeout") or 10),
			)
		elif kind == "Ollama":
			request_json("GET", f"{url}/api/tags", timeout=int(connector.get("timeout") or 10))
		elif kind == "OCR":
			if connector.get("ocr_mode") == "HTTP" and url:
				request_json("GET", url, timeout=int(connector.get("timeout") or 10))
		elif kind == "Frappe-Connect":
			request_json("GET", f"{url}/api/v1/health", timeout=int(connector.get("timeout") or 10))
		elif kind in {"WAHA", "WhatsApp Web.js"}:
			path = "/api/sessions" if kind == "WAHA" else "/health"
			request_json(
				"GET",
				f"{url}{path}",
				headers=_auth(connector),
				timeout=int(connector.get("timeout") or 10),
				verify=bool(connector.get("verify_ssl", 1)),
			)
		status.connected = True
	except Exception as exc:
		status.connected = False
		status.last_error = str(exc)[:140]
	return status


def _auth(connector) -> dict | None:
	key = safe_password(connector, "api_key")
	if not key:
		return None
	return {"X-Api-Key": key, "Authorization": f"Bearer {key}"}
