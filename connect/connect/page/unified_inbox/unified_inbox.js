frappe.pages["connect-inbox"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Unified Inbox"),
		single_column: true,
	});
	page.add_inner_button(__("Conversations"), () => frappe.set_route("List", "Conversation"));
	page.add_inner_button(__("New Internal Chat"), () => {
		const d = new frappe.ui.Dialog({
			title: __("Internal Chat"),
			fields: [{ fieldname: "user", label: __("User"), fieldtype: "Link", options: "User", reqd: 1 }],
			primary_action_label: __("Open"),
			primary_action(values) {
				frappe.call({
					method: "connect.api.send.send_message",
					args: {
						channel: "Internal",
						recipient: values.user,
						message: __("Conversation started"),
					},
					callback(r) {
						d.hide();
						if (r.message && r.message.conversation) {
							frappe.set_route("Form", "Conversation", r.message.conversation);
						}
					},
				});
			},
		});
		d.show();
	});

	const $body = $(page.body).html(`<div class="padding connect-inbox-list"></div>`);
	frappe.call({
		method: "connect.api.inbox.list_conversations",
		callback(r) {
			const rows = (r.message || [])
				.map((c) => {
					return `<tr class="connect-conv" data-name="${frappe.utils.escape_html(c.name)}">
						<td>${frappe.utils.escape_html(c.channel || "")}</td>
						<td>${frappe.utils.escape_html(c.party || c.contact_identifier || "")}</td>
						<td>${frappe.utils.escape_html(c.last_message || "")}</td>
						<td>${frappe.utils.escape_html(c.last_message_time || "")}</td>
						<td>${c.unread_count || 0}</td>
					</tr>`;
				})
				.join("");
			$body.find(".connect-inbox-list").html(`
				<table class="table table-hover">
					<thead><tr>
						<th>${__("Channel")}</th>
						<th>${__("Party")}</th>
						<th>${__("Last message")}</th>
						<th>${__("When")}</th>
						<th>${__("Unread")}</th>
					</tr></thead>
					<tbody>${rows || `<tr><td colspan="5" class="text-muted">${__("No conversations yet")}</td></tr>`}</tbody>
				</table>
			`);
			$body.find("tr.connect-conv").on("click", function () {
				frappe.set_route("Form", "Conversation", $(this).data("name"));
			});
		},
	});
};
