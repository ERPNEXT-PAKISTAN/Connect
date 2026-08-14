# Copyright (c) 2026, Connect contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ChannelAccount(Document):
	def validate(self):
		if self.is_default and self.channel:
			pass

