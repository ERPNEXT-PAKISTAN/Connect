# Connect

Lightweight **Frappe/ERPNext** messaging app. Installed in the Bench, used from Desk.

Connect is **not** the standalone [Frappe-Connect](https://github.com) Node gateway. That project stays separate. This app talks to providers over HTTP and to optional external services (WAHA, n8n, Ollama, OCR, Frappe-Connect) only as connectors.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## Install

```bash
cd ~/frappe-bench
bench get-app <repository-url>
bench --site <site> install-app connect
bench --site <site> migrate
bench build --app connect
bench restart
```

Requires Frappe + ERPNext. No PostgreSQL, extra Redis, Node backend, or Docker service is needed for Connect itself.

After install, Dashboard, Internal Chat, Inbox, Templates, Rules, PDF, Email (if an Email Account exists), Webhooks, Logs, and Settings work without Telegram, WAHA, Firebase, n8n, or Ollama.

## What stays outside Connect

| Service | Role |
| --- | --- |
| WAHA | WhatsApp Web sessions |
| whatsapp-web.js | Alternate unofficial WhatsApp runtime |
| n8n | Optional advanced workflows |
| Ollama | Optional AI |
| OCR / Tesseract | Optional document OCR |
| Frappe-Connect | Optional standalone gateway |

Configure them under **Connect → Settings → External Connectors**. Do not install those runtimes into this Python app.

## License

MIT
