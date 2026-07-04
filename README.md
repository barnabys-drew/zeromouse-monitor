# Zeromouse Blade Stock Monitor

[![Smoke Tests](https://github.com/barnabys-drew/zeromouse-monitor/actions/workflows/smoke.yml/badge.svg)](https://github.com/barnabys-drew/zeromouse-monitor/actions/workflows/smoke.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)

Watches [zeromouse.co/products/blade](https://zeromouse.co/products/blade) and pushes a notification to your phone the moment the mouse is back in stock.

- **Reliable checks** — reads Shopify's product JSON (variant availability), not fragile page-text scraping
- **Phone push via [ntfy](https://ntfy.sh)** — no accounts, no API keys, just a topic name
- **Spam-safe** — configurable cooldown between alerts, persisted across restarts
- **Self-watching** — alerts you if the monitor itself starts failing, so it can't die silently
- **One command** — `docker compose up -d` and forget about it

## Prerequisites

- Docker and Docker Compose
- The [ntfy app](https://ntfy.sh) on your phone

## Phone Setup (ntfy)

1. Install the **ntfy** app:
   - **Android**: [Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - **iPhone**: [App Store](https://apps.apple.com/app/ntfy/id1625396347)

2. Open the app and tap the **+** button to subscribe to a topic.

3. Type a topic name, e.g. `zeromouse-blade-drew`. This must **exactly match** the `NTFY_TOPIC` in your `.env` file. Pick something hard to guess — the topic name is the only thing keeping notifications private.

4. Tap **Subscribe**. You'll now receive a push notification whenever the monitor sends one.

## Quick Start

1. Create a `.env` file in this directory (start from the template):

```bash
cp .env.example .env
```

Then set at least `NTFY_TOPIC` (must match the topic you subscribed to in the ntfy app), for example:

```
NTFY_TOPIC=zeromouse-blade-drew
```

2. **Test that notifications reach your phone** (do this first!):

```bash
docker compose run --rm monitor python monitor.py --test
```

You should get a push notification on your phone within a few seconds. If not, double-check that the topic name in `.env` matches what you subscribed to in the app.

3. Start the monitor:

```bash
docker compose up -d
```

4. Check logs:

```bash
docker compose logs -f
```

5. Stop the monitor:

```bash
docker compose down
```

## Configuration

| Variable                  | Description                                            | Default              |
|---------------------------|--------------------------------------------------------|----------------------|
| `NTFY_TOPIC`              | Your ntfy topic name (must match the app)              | —                    |
| `NTFY_SERVER`             | ntfy server URL                                        | `https://ntfy.sh`    |
| `CHECK_INTERVAL`          | Seconds between checks                                 | `900`                |
| `NOTIFY_COOLDOWN`         | Seconds between repeat in-stock notifications          | `3600`               |
| `FAILURE_ALERT_THRESHOLD` | Consecutive failed checks before a "monitor is failing" alert | `8`           |
| `STATE_FILE`              | Cooldown state path (restart-safe)                     | `data/.zeromouse_state.json` |

## How It Works

- Fetches the Shopify product JSON ([`/products/blade.json`](https://zeromouse.co/products/blade.json)) every `CHECK_INTERVAL` seconds.
- If **any variant** reports `available: true`, it sends a push notification via [ntfy.sh](https://ntfy.sh). Tapping the notification opens the product page.
- After sending a notification, it waits `NOTIFY_COOLDOWN` seconds (default 1 hour) before sending another, to avoid spam.
- The last notification timestamp is persisted to `STATE_FILE`, so restarts keep cooldown behavior.
- **Watchdog:** if `FAILURE_ALERT_THRESHOLD` checks fail in a row (network errors, blocked requests, or an unexpected JSON shape), it sends a one-time "monitor is failing" alert so a silently broken monitor doesn't go unnoticed. The alert re-arms after the next successful check.
- The container auto-restarts on failure thanks to `restart: unless-stopped`.
- No passwords or API keys are needed — just a topic name.

## Development

```bash
pip install -r requirements.txt pytest
pytest
```

Run a single check without the daemon loop (useful for cron):

```bash
python monitor.py --once
```

## Homelab Notes

If you run several containers from `~/code` on a spare PC (shared scheduling, logs, optional GPU for other tools), see [docs/LOCAL_INFRA_ROADMAP.md](docs/LOCAL_INFRA_ROADMAP.md). The same note exists in **concentration-manager** and **catastrophe-analyzer**.

## License

[MIT](LICENSE)
