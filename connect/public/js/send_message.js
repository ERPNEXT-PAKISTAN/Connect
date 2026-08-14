frappe.provide("connect");

connect.SEND_DOCTYPES_FALLBACK = [
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Delivery Note",
	"Payment Entry",
	"Purchase Order",
	"Purchase Invoice",
	"Customer",
	"Supplier",
	"Lead",
	"Issue",
];

connect.get_enabled_doctypes = function () {
	const boot = (frappe.boot && frappe.boot.connect) || {};
	if (!boot.enable_send_message_button) {
		return [];
	}
	return boot.enabled_doctypes && boot.enabled_doctypes.length
		? boot.enabled_doctypes
		: connect.SEND_DOCTYPES_FALLBACK;
};

connect.open_send_dialog = function (frm) {
	const doc = frm.doc;
	const fields = [
		{
			fieldname: "channel",
			label: __("Channel"),
			fieldtype: "Select",
			options: ["WhatsApp", "Telegram", "Firebase", "Slack", "Discord", "Email", "Webhook", "Internal"].join("\n"),
			reqd: 1,
			default: "WhatsApp",
		},
		{
			fieldname: "account",
			label: __("Account"),
			fieldtype: "Link",
			options: "Channel Account",
		},
		{
			fieldname: "recipient",
			label: __("Recipient"),
			fieldtype: "Data",
			reqd: 1,
			default: connect.guess_recipient(doc),
		},
		{
			fieldname: "template",
			label: __("Template"),
			fieldtype: "Link",
			options: "Message Template",
		},
		{
			fieldname: "print_format",
			label: __("Print Format"),
			fieldtype: "Link",
			options: "Print Format",
			get_query: () => ({ filters: { doc_type: doc.doctype } }),
		},
		{
			fieldname: "attach_pdf",
			label: __("Attach PDF"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "message",
			label: __("Message"),
			fieldtype: "Small Text",
			default: __("Please find attached {0} {1}.", [doc.doctype, doc.name]),
		},
	];

	const d = new frappe.ui.Dialog({
		title: __("Send Message"),
		fields: fields,
		primary_action_label: __("Send"),
		primary_action(values) {
			d.disable_primary_action();
			frappe.call({
				method: "connect.api.send.send_message",
				args: {
					channel: values.channel,
					account: values.account,
					recipient: values.recipient,
					template: values.template,
					print_format: values.print_format,
					attach_pdf: values.attach_pdf ? 1 : 0,
					message: values.message,
					reference_doctype: doc.doctype,
					reference_name: doc.name,
				},
				callback(r) {
					d.enable_primary_action();
					if (!r.exc) {
						frappe.show_alert({ message: __("Message queued"), indicator: "green" });
						d.hide();
					}
				},
				error() {
					d.enable_primary_action();
				},
			});
		},
	});
	d.set_query("account", () => ({
		filters: { enabled: 1, channel: d.get_value("channel") || "WhatsApp" },
	}));
	d.show();
};

connect.guess_recipient = function (doc) {
	return (
		doc.contact_mobile ||
		doc.mobile_no ||
		doc.customer_mobile_no ||
		doc.contact_email ||
		doc.email_id ||
		""
	);
};

connect.attach_send_button = function (frm) {
	if (!frm || frm.is_new()) {
		return;
	}
	const enabled = connect.get_enabled_doctypes();
	if (enabled.indexOf(frm.doctype) === -1) {
		return;
	}
	if (frm.custom_buttons && frm.custom_buttons[__("Send Message")]) {
		return;
	}
	frm.add_custom_button(__("Send Message"), () => connect.open_send_dialog(frm));
};

$(document).on("form-refresh", function (_e, frm) {
	try {
		connect.attach_send_button(frm);
	} catch (err) {
		/* isolated: never break the form */
	}
});
