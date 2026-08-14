
frappe.ui.form.on("External Connector", {
	refresh(frm) {
		frm.add_custom_button(__("Test Connection"), () => {
			frappe.call({
				method: "connect.api.status.test_connection",
				args: { doctype: frm.doc.doctype, name: frm.doc.name },
				freeze: true,
				callback(r) {
					frm.reload_doc();
					const s = r.message || {};
					frappe.msgprint(s.connected ? __("Connected") : (s.last_error || __("Not connected")));
				},
			});
		});
	},
});
