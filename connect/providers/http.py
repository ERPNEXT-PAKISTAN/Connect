# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""HTTP helper. Never raises out of Connect — callers wrap ProviderUnavailable."""

from __future__ import annotations

from typing import Any

import frappe

from connect.providers.exceptions import ProviderUnavailable


def request_json(
	method: str,
	url: str,
	*,
	headers: dict | None = None,
	json: dict | None = None,
	data: Any = None,
	timeout: int | float = 15,
	verify: bool = True,
	files: dict | None = None,
) -> dict[str, Any]:
	import requests

	try:
		resp = requests.request(
			method=method.upper(),
			url=url,
			headers=headers,
			json=json,
			data=data,
			timeout=timeout,
			verify=verify,
			files=files,
		)
	except Exception as exc:
		raise ProviderUnavailable(str(exc)) from exc

	try:
		body = resp.json() if resp.content else {}
	except Exception:
		body = {"text": (resp.text or "")[:2000]}

	if resp.status_code >= 400:
		raise ProviderUnavailable(f"HTTP {resp.status_code}: {body or resp.text[:300]}")
	return body if isinstance(body, dict) else {"data": body}


def safe_password(doc, field: str) -> str:
	if not doc:
		return ""
	try:
		return doc.get_password(field) or ""
	except Exception:
		return ""


def record_account_status(account, ok: bool, error: str | None = None) -> None:
	if not account:
		return
	try:
		from frappe.utils import now_datetime

		account.db_set("connection_status", "Connected" if ok else "Error", update_modified=False)
		if ok:
			account.db_set("last_successful_connection", now_datetime(), update_modified=False)
			account.db_set("last_error", "", update_modified=False)
		else:
			account.db_set("last_error", (error or "")[:140], update_modified=False)
	except Exception:
		frappe.log_error(title="Connect status write failed")
