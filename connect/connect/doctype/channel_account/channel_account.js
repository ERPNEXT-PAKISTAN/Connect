
frappe.ui.form.on("Channel Account", {
	refresh(frm) {
		frm.add_custom_button(__("Test Connection"), () => {
			frappe.call({
				method: "connect.api.status.test_connection",
				args: { doctype: frm.doc.doctype, name: frm.doc.name },
				freeze: true,
				callback(r) {
					frm.reload_doc();
					const s = r.message || {};
					frappe.msgprint({
						title: __("Test Connection"),
						indicator: s.connected ? "green" : "orange",
						message: `${__("Connected")}: ${s.connected ? __("Yes") : __("No")}<br>
							${__("Configured")}: ${s.configured ? __("Yes") : __("No")}<br>
							${s.last_error || s.detail || ""}`,
					});
				},
			});
		});
		if (!frm.is_new()) {
			frm.add_custom_button(__("Send Test"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Send Test"),
					fields: [
						{ fieldname: "recipient", label: __("Recipient"), fieldtype: "Data", reqd: 1 },
						{ fieldname: "text", label: __("Message"), fieldtype: "Small Text", default: "Connect test message" },
					],
					primary_action_label: __("Send"),
					primary_action(values) {
						frappe.call({
							method: "connect.api.status.send_test",
							args: { account: frm.doc.name, recipient: values.recipient, text: values.text },
							callback(r) {
								d.hide();
								frappe.msgprint(r.message && r.message.ok ? __("Sent") : (r.message && r.message.error) || __("Failed"));
							},
						});
					},
				});
				d.show();
			});
		}
	},
	channel(frm) {
		const map = {
			WhatsApp: ["WAHA", "WhatsApp Web.js", "Meta Cloud API"],
			Telegram: ["Telegram"],
			Firebase: ["Firebase"],
			Slack: ["Slack"],
			Discord: ["Discord"],
			Email: ["Email"],
			Webhook: ["Webhook"],
			Internal: ["Internal"],
			"Frappe-Connect": ["Frappe-Connect"],
		};
		const options = map[frm.doc.channel] || [];
		frm.set_df_property("provider", "options", options.join("\n"));
		if (options.length === 1) {
			frm.set_value("provider", options[0]);
		}
	},
});
