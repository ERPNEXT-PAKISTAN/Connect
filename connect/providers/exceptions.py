# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

"""Provider exceptions. Failures stay isolated to the calling provider."""


class ConnectProviderError(Exception):
	"""Base error for a single provider call. Never used as app-wide health."""


class ProviderNotConfigured(ConnectProviderError):
	pass


class ProviderDisabled(ConnectProviderError):
	pass


class ProviderUnavailable(ConnectProviderError):
	"""External runtime missing or HTTP failed. Other channels keep working."""


class InvalidRecipient(ConnectProviderError):
	pass
