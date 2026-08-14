# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Firebase Cloud Messaging via HTTP v1. No firebase-admin SDK."""

from __future__ import annotations

import json
import time

from connect.providers.base import MessagingProvider
from connect.providers.exceptions import ProviderUnavailable
from connect.providers.http import record_account_status, request_json, safe_password
from connect.providers.types import ProviderStatus, SendResult


class FirebaseProvider(MessagingProvider):
	channel = "Firebase"
	provider_key = "Firebase"
	kind = "builtin"

	def _credentials(self) -> dict:
		raw = safe_password(self.account, "firebase_service_account")
		if not raw:
			return {}
		try:
			return json.loads(raw)
		except Exception:
			return {}

	def get_status(self) -> ProviderStatus:
		creds = self._credentials()
		project = (self.account.get("firebase_project_id") if self.account else None) or creds.get("project_id")
		return self._base_status(configured=bool(creds and project), detail="FCM HTTP v1")

	def test_connection(self) -> ProviderStatus:
		status = self.get_status()
		try:
			self._access_token()
			status.connected = True
			record_account_status(self.account, True)
		except Exception as exc:
			status.connected = False
			status.last_error = str(exc)[:140]
			record_account_status(self.account, False, str(exc))
		return status

	def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
		self._require_enabled()
		creds = self._credentials()
		project = (self.account.get("firebase_project_id") if self.account else None) or creds.get("project_id")
		self._require_configured(creds, project)
		token = self._access_token()
		target_type = kwargs.get("target_type") or "token"
		message: dict = {"notification": {"title": kwargs.get("title") or "Connect", "body": text}}
		if target_type == "topic":
			message["topic"] = recipient or (self.account.get("firebase_default_topic") if self.account else None)
		elif target_type == "condition":
			message["condition"] = recipient
		else:
			self.validate_recipient(recipient)
			message["token"] = recipient
		body = request_json(
			"POST",
			f"https://fcm.googleapis.com/v1/projects/{project}/messages:send",
			headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
			json={"message": message},
			timeout=20,
		)
		record_account_status(self.account, True)
		return SendResult(ok=True, external_id=str(body.get("name") or ""), raw=body)

	def _access_token(self) -> str:
		creds = self._credentials()
		if not creds:
			raise ProviderUnavailable("Firebase service account is missing")
		try:
			import jwt
		except Exception as exc:
			raise ProviderUnavailable("PyJWT is required for Firebase") from exc

		now = int(time.time())
		payload = {
			"iss": creds.get("client_email"),
			"sub": creds.get("client_email"),
			"aud": "https://oauth2.googleapis.com/token",
			"iat": now,
			"exp": now + 3600,
			"scope": "https://www.googleapis.com/auth/firebase.messaging",
		}
		assertion = jwt.encode(payload, creds.get("private_key"), algorithm="RS256")
		if isinstance(assertion, bytes):
			assertion = assertion.decode()
		body = request_json(
			"POST",
			"https://oauth2.googleapis.com/token",
			data={
				"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
				"assertion": assertion,
			},
			timeout=20,
		)
		token = body.get("access_token")
		if not token:
			raise ProviderUnavailable("Firebase token exchange failed")
		return token
