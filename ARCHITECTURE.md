# Connect — Native Frappe App Architecture

**App name:** Connect  
**Technical package:** `connect`  
**Kind:** Lightweight Frappe/ERPNext app installed in the Bench  
**Date:** 2026-08-15

Connect lives **inside ERPNext Desk**. It is not a standalone Node/Docker application.

The separate project **Frappe-Connect** (`/home/frappe/frappe-connect`) is a different product. Do not merge the two. Do not change Frappe-Connect as part of Connect work. They may talk over HTTP later; neither is required by the other.

---

## 1. Decision rule

> If the provider offers a normal HTTP API and does not require a persistent local runtime, implement the connector **directly inside Connect**.
>
> If it requires browser automation, a persistent daemon, an AI model runtime, an OCR engine, a workflow engine, or another heavy process, keep it **outside** Connect and talk to it through an **External Connector**.

Do not create a Docker service merely to call an HTTP API.

Implement a feature inside Connect when it can be done safely with:

- Frappe APIs
- Python HTTP requests
- provider REST APIs and webhooks
- Frappe background jobs, scheduler, realtime
- Frappe Email, Print/PDF
- Frappe Users, Roles, Permissions

---

## 2. What Connect is (and is not)

| Connect is | Connect is not |
| --- | --- |
| A Bench app: `bench get-app` / `bench install-app connect` | A second ERPNext |
| Desk workspace, DocTypes, pages | Port 8080, PostgreSQL, React server |
| MariaDB via the site database | Its own database |
| Frappe users and sessions | A separate auth server |
| `frappe.enqueue` + site Redis | n8n as the base queue |
| Optional HTTP clients | WAHA / Puppeteer / Ollama / Tesseract bundled in |

Install:

```bash
cd ~/frappe-bench
bench get-app <repository-url>
bench --site <site> install-app connect
bench --site <site> migrate
bench build --app connect
bench restart
```

After install, with **no** optional services, these must work:

Dashboard, Internal Chat, Unified Inbox, Messages, Conversations, Templates, basic Notification Rules, system notifications, PDF generation, Email (if an Email Account exists), Webhooks, Delivery Logs, Settings.

---

## 3. Two products, one host

```text
ERPNext / Frappe (native Bench)
└── Connect                    ← this app (Desk)

Optional, outside Connect
├── WAHA                       HTTP API
├── whatsapp-web.js service    HTTP API
├── n8n                        HTTP / webhooks
├── Ollama                     HTTP API
├── OCR service                HTTP / executable
└── Frappe-Connect             HTTP API (standalone Node app)
```

Frappe-Connect remains a self-hosted Node + PostgreSQL gateway. Connect may optionally point at it as an External Connector. Connect must not import, embed, or depend on that repository.

---

## 4. Package layout

```text
connect/
├── hooks.py
├── install.py
├── modules.txt                  # Connect
├── api/                         # whitelisted HTTP
│   ├── send.py
│   ├── status.py
│   ├── inbox.py
│   └── webhooks.py
├── providers/                   # channel-agnostic interface
│   ├── base.py                  # MessagingProvider
│   ├── registry.py
│   ├── status.py
│   └── <provider>.py
├── queue/jobs.py                # frappe.enqueue workers
├── rules.py                     # Notification Rule dispatcher
├── pdf.py                       # Frappe print/PDF wrapper
├── chat.py                      # Internal Chat
├── connect/                     # module
│   ├── doctype/
│   ├── page/
│   └── workspace/
└── public/js/send_message.js    # reusable Desk action
```

Business logic lives in `providers/`, `queue/`, `api/`, and `chat.py` — not only in DocType controllers.

Python dependencies stay empty unless Frappe cannot already do the job. No Puppeteer, Chromium, Ollama, n8n, WAHA, PostgreSQL, extra Redis, or Node server as app dependencies.

HTTP providers use `frappe.integrations.utils.make_request` / `requests` already present in the environment. Firebase uses the FCM HTTP v1 API with a service-account JWT (PyJWT/cryptography already in Frappe) — not `firebase-admin`.

---

## 5. Channel vs provider

Keep these separate.

| Channel | Providers that may serve it |
| --- | --- |
| WhatsApp | WAHA, WhatsApp Web.js, Meta Cloud API |
| Telegram | Telegram (built-in Bot API) |
| Firebase | Firebase (FCM HTTP v1) |
| Slack | Slack (webhook or bot) |
| Discord | Discord (webhook or bot) |
| Email | Email (Frappe Email Account) |
| Webhook | Generic webhook |
| Internal | Internal (Frappe users only) |
| Frappe-Connect | Frappe-Connect (optional external gateway) |

Example: Channel = WhatsApp, Provider = WAHA. Another account may use Channel = WhatsApp, Provider = Meta Cloud API.

Only one WhatsApp provider may control a given phone number / session.

DocTypes and UI always store **channel** and **provider** as distinct fields. Business logic (inbox, templates, rules, PDF attach) talks to `MessagingProvider`, never to WAHA or Telegram payloads.

---

## 6. Provider interface

```python
class MessagingProvider:
    channel: str
    provider_key: str
    kind: str  # "builtin" | "external"

    def get_status(self) -> ProviderStatus: ...
    def test_connection(self) -> ProviderStatus: ...
    def send_text(self, recipient, text, **kwargs) -> SendResult: ...
    def send_document(self, recipient, file, caption=None, **kwargs) -> SendResult: ...
    def send_image(self, recipient, file, caption=None, **kwargs) -> SendResult: ...
    def validate_recipient(self, recipient) -> None: ...
    def handle_webhook(self, payload, headers=None) -> IncomingMessage | None: ...
```

`ProviderStatus` always reports, independently:

| Flag | Meaning |
| --- | --- |
| Installed / Available | Built-in code exists, or external service is reachable enough to detect |
| Configured | Required settings are present |
| Enabled | User turned it on |
| Connected | Last test/send succeeded |
| Last successful connection | Timestamp |
| Last error | Isolated to this provider |

Detection never auto-enables a provider.

`get_status()` must not throw out to the rest of Connect. Optional failures stay on that provider.

---

## 7. Built-in vs external

### Built-in (direct HTTP from Python)

| Provider | Why built-in |
| --- | --- |
| Telegram | Public Bot API |
| Firebase | FCM HTTP v1 |
| Slack | Incoming webhook / Web API |
| Discord | Incoming webhook / Bot API |
| Meta WhatsApp Cloud API | Graph API |
| Email | Frappe Email Account (`frappe.sendmail`) |
| Generic webhooks | Incoming + outgoing HTTP |
| Internal Chat | Frappe users + realtime |

No Telegram/Slack/Discord/WhatsApp/Firebase container is required.

### External connectors (settings under Connect → Settings → External Connectors)

| Connector | Why external |
| --- | --- |
| WAHA | Persistent WhatsApp Web session (browser engine) |
| whatsapp-web.js | Node + Puppeteer/Chromium |
| n8n | Workflow engine; optional advanced automation only |
| Ollama | Model runtime |
| OCR | Tesseract or cloud OCR process |
| Frappe-Connect | Separate standalone product |

Connect only stores URL/credentials and calls HTTP. It does not install or embed those runtimes.

If Ollama, n8n, WAHA, Firebase, or Telegram is down, **only that feature** is unavailable. Core Connect health follows Frappe + Connect DocTypes/jobs.

---

## 8. Data model

Lightweight DocTypes. Child tables instead of extra DocTypes where possible.

| DocType | Role |
| --- | --- |
| **Connect Settings** | Single: general, send-message defaults, queue retries, advanced |
| **Channel Account** | One configured identity on a channel+provider |
| **External Connector** | WAHA / web.js / n8n / Ollama / OCR / Frappe-Connect |
| **Messaging Contact** | ERPNext party mapped to messaging identities |
| **External Identity** | Child of contact: channel, provider, identifier |
| **Conversation** | Thread: channel, account, contact/party, assignee, unread |
| **Message** | Incoming / Outgoing / Internal; queue status |
| **Message Attachment** | Child of Message |
| **Message Template** | Channel-aware body + optional PDF |
| **Notification Rule** | DocType event → channel → recipient → template/PDF |
| **Delivery Log** | Per-attempt log (not the message itself) |
| **Webhook Endpoint** | Incoming or outgoing; HMAC, bearer, headers, retries |
| **Connect Enabled DocType** | Child of Settings: where Send Message appears |
| **Connect Custom Header** | Child of Webhook Endpoint |
| **Connect Allowed Principal** | Child of Channel Account (Telegram allow-list, etc.) |

### Conversation

Channel, Account, Contact, Customer/Supplier/Lead/User (Dynamic Link `party`), Assigned To, Status, Last Message, Last Message Time, Unread Count. `conversation_type`: External, Internal, Group (group later).

### Message

Conversation, Direction (`Incoming` / `Outgoing` / `Internal`), Channel, Provider, Sender, Recipient, Message, Message Type, Attachment, External Message ID, Status, Sent/Delivered/Read/Failed At, Error, Reference DocType/Name, Metadata.

Statuses: `Queued` → `Sending` → `Sent` → `Delivered` → `Read`, or `Failed` / `Cancelled`.

---

## 9. Message flow

```text
ERPNext event or Desk "Send Message"
        │
        ▼
   Message (Queued)
        │
        ▼
   frappe.enqueue  (after commit)
        │
        ▼
   Provider.send_*
        │
        ├── success → Sent (+ Delivery Log)
        └── error   → Failed, retry/backoff on the same job
```

Incoming:

```text
Provider webhook
    → /api/method/connect.api.webhooks.receive
    → provider.handle_webhook()
    → Message + Conversation
    → Unified Inbox
    → frappe.publish_realtime
```

WAHA example:

```text
WhatsApp → WAHA → webhook → Connect API → Message → Conversation → Inbox
```

Do not send provider HTTP inside a slow `on_submit` transaction. Enqueue after commit. n8n is not the queue.

---

## 10. Internal Chat

Works with ERPNext + Connect only. No external provider.

- User-to-user conversations (`conversation_type = Internal`)
- Mentions (`@user`)
- Attachments (Frappe File)
- Link to an ERPNext document (`reference_doctype` / `reference_name`)
- Realtime via `frappe.publish_realtime` on `connect:message`
- Unread count on Conversation
- Group conversations: schema-ready, not required for v0

---

## 11. Send Message action

Reusable Desk dialog, not hardcoded to a few DocTypes.

`Connect Settings` child table **Enabled DocTypes** defaults to Quotation, Sales Order, Sales Invoice, Delivery Note, Payment Entry, Purchase Order, Purchase Invoice, Customer, Supplier, Lead, Issue — and can add any other DocType.

Dialog fields: Channel, Account, Recipient, Template, Print Format, Attach PDF, Message, Send.

PDF uses existing Print Format generation (`connect.pdf.get_pdf`). Connect does not redraw invoices.

---

## 12. Notification Rules

Simple automation inside Connect:

```text
Sales Invoice on_submit → WhatsApp → Customer → attach PDF
Payment Entry on_submit → Firebase → Sales Person
```

Hook `doc_events` on `*` dispatches to `connect.rules`, skips Connect’s own DocTypes, matches enabled rules, writes a Queued Message, enqueues.

Multi-step / branching workflows may optionally call n8n. Core messaging must not require n8n.

---

## 13. Settings UI (Desk)

```text
Connect
├── Dashboard
├── Unified Inbox
├── Conversations / Messages
└── Settings
    ├── General                  (Connect Settings)
    ├── Channels                 (Channel Account, filtered)
    │   ├── WhatsApp
    │   ├── Telegram
    │   ├── Firebase
    │   ├── Email
    │   ├── Slack
    │   └── Discord
    ├── External Connectors      (External Connector)
    │   ├── WAHA
    │   ├── whatsapp-web.js
    │   ├── n8n
    │   ├── Ollama
    │   ├── OCR
    │   └── Frappe-Connect
    ├── Webhooks
    ├── Templates
    ├── Rules
    ├── Permissions              (Connect Manager / Connect User)
    └── Advanced
```

Every Channel Account and External Connector form has **Test Connection**. Where it is meaningful, **Send Test** (Telegram, Firebase, WAHA, Email, Slack, Discord).

---

## 14. Permissions

Roles created on install:

| Role | Purpose |
| --- | --- |
| Connect Manager | Settings, connectors, rules, all conversations |
| Connect User | Inbox, send, internal chat, own assigned conversations |

Secrets use Frappe `Password` fields (site encryption). Tokens are never written to Error Log or Delivery Log bodies.

Webhook receive methods are guest-whitelisted only with verify-token / HMAC / shared secret checks.

---

## 15. Graceful failure

Connect core health is Frappe + this app.

| Failure | Effect |
| --- | --- |
| Ollama down | AI helpers unavailable |
| n8n down | Optional n8n workflows unavailable |
| WAHA down | WAHA WhatsApp accounts unavailable |
| Firebase down | Push unavailable |
| Telegram down | Telegram unavailable |
| Email Account missing | Email channel unavailable; rest continues |

`connect.api.status.health` returns `ok` when the site and Connect DocTypes load. Optional providers appear as `disabled` or `error` on their own keys and cannot flip overall health to failed.

---

## 16. Implementation order

1. App skeleton, DocTypes, workspace, permissions  
2. Internal Chat + Inbox + Messages  
3. Queue + Email + PDF + Send Message dialog  
4. Templates + Notification Rules  
5. Webhooks (generic in/out)  
6. Telegram, Slack, Discord, Meta Cloud API, Firebase  
7. External: WAHA, then web.js, n8n, Ollama, OCR, Frappe-Connect  

Each provider is feature-flagged by `enabled` on its Channel Account / External Connector. Defaults are off except Internal Chat and Email-if-configured.

---

## 17. Out of scope

- Installing or embedding WAHA, Chromium, n8n, Ollama, Tesseract
- Changing Frappe-Connect architecture or repository
- Replacing Raven; Internal Chat is a Connect feature, not a Raven fork
- Direct SMTP unless a later “Direct SMTP” mode is explicitly added (Email Account first)
