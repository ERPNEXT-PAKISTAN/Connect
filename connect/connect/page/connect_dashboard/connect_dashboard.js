frappe.pages["connect-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Connect"),
		single_column: true,
	});

	page.add_inner_button(__("Inbox"), () => frappe.set_route("connect-inbox"));
	page.add_inner_button(__("Settings"), () => frappe.set_route("Form", "Connect Settings"));

	const $body = $(page.body).html(`
		<div class="padding">
			<p class="text-muted">${__("Native Frappe messaging. Optional providers stay isolated.")}</p>
			<div class="connect-health"></div>
		</div>
	`);

	frappe.call({
		method: "connect.api.status.health",
		callback(r) {
			const data = r.message || {};
			const rows = (data.providers || [])
				.map((p) => {
					const state = p.enabled ? (p.connected ? "Connected" : p.configured ? "Configured" : "Enabled") : "Off";
					return `<tr>
						<td>${frappe.utils.escape_html(p.channel || "")}</td>
						<td>${frappe.utils.escape_html(p.provider || "")}</td>
						<td>${p.kind === "external" ? __("External") : __("Built into Connect")}</td>
						<td>${p.configured ? __("Yes") : __("No")}</td>
						<td>${p.enabled ? __("Yes") : __("No")}</td>
						<td>${frappe.utils.escape_html(state)}</td>
						<td class="text-muted">${frappe.utils.escape_html(p.last_error || "")}</td>
					</tr>`;
				})
				.join("");
			$body.find(".connect-health").html(`
				<p><b>${__("App health")}:</b> ${data.ok ? __("OK") : __("Degraded")}</p>
				<table class="table table-bordered">
					<thead><tr>
						<th>${__("Channel")}</th>
						<th>${__("Provider")}</th>
						<th>${__("Type")}</th>
						<th>${__("Configured")}</th>
						<th>${__("Enabled")}</th>
						<th>${__("Connection")}</th>
						<th>${__("Last error")}</th>
					</tr></thead>
					<tbody>${rows}</tbody>
				</table>
			`);
		},
	});
};
