app_name = "connect"
app_title = "Connect"
app_publisher = "Connect contributors"
app_description = "Lightweight native messaging, inbox, and provider connectors for ERPNext"
app_email = "connect@local"
app_license = "mit"
app_logo_url = "/assets/connect/images/connect-logo.svg"
app_home = "/app/connect"

required_apps = ["frappe"]

add_to_apps_screen = [
	{
		"name": "connect",
		"logo": app_logo_url,
		"title": app_title,
		"route": app_home,
	}
]

app_include_js = ["/assets/connect/js/send_message.js"]
app_include_css = ["/assets/connect/css/connect.css"]

after_install = "connect.install.after_install"
after_migrate = "connect.install.after_migrate"

extend_bootinfo = "connect.boot.boot_session"

doc_events = {
	"*": {
		"on_submit": "connect.rules.on_submit",
		"on_cancel": "connect.rules.on_cancel",
		"on_update": "connect.rules.on_update",
	}
}

scheduler_events = {
	"cron": {
		"*/5 * * * *": [
			"connect.queue.jobs.retry_failed_messages",
		]
	}
}

permission_query_conditions = {
	"Conversation": "connect.permissions.conversation_query",
	"Message": "connect.permissions.message_query",
}

has_permission = {
	"Conversation": "connect.permissions.conversation_has_permission",
	"Message": "connect.permissions.message_has_permission",
}
