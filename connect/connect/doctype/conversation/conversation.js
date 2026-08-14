frappe.ui.form.on("Conversation", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Open Inbox"), () => frappe.set_route("connect-inbox"));
		frm.add_custom_button(__("Reply"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Reply"),
				fields: [
					{ fieldname: "message", label: __("Message"), fieldtype: "Small Text", reqd: 1 },
				],
				primary_action_label: __("Send"),
				primary_action(values) {
					const recipient =
						frm.doc.conversation_type === "Internal"
							? frm.doc.party === frappe.session.user
								? frm.doc.assigned_to
								: frm.doc.party
							: frm.doc.contact_identifier;
					frappe.call({
						method: "connect.api.send.send_message",
						args: {
							channel: frm.doc.channel,
							account: frm.doc.account,
							provider: frm.doc.provider,
							recipient: recipient,
							message: values.message,
							conversation: frm.doc.name,
						},
						callback(r) {
							d.hide();
							if (!r.exc) {
								frm.reload_doc();
							}
						},
					});
				},
			});
			d.show();
		});
	},
});
