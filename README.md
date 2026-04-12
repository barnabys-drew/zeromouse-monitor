# Zeromouse Blade Stock Monitor

Monitors [zeromouse.co/products/blade](https://zeromouse.co/products/blade) every 15 minutes and sends a push notification to your phone when the mouse is available for purchase.

**Homelab / multi-tool context:** If you run several containers from `~/code` on a spare PC (shared scheduling, logs, optional GPU for other tools), see [docs/LOCAL_INFRA_ROADMAP.md](docs/LOCAL_INFRA_ROADMAP.md). The same note exists in **concentration-manager** and **catastrophe-analyzer**.

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

1. Create a `.env` file in this directory:

```
NTFY_TOPIC=zeromouse-blade-drew
```

| Variable         | Description                              | Default              |
|------------------|------------------------------------------|----------------------|
| `NTFY_TOPIC`     | Your ntfy topic name (must match the app)| —                    |
| `NTFY_SERVER`    | ntfy server URL                          | `https://ntfy.sh`    |
| `CHECK_INTERVAL` | Seconds between checks                   | `900`                |
| `STATE_FILE`     | Cooldown state path (restart-safe)       | `data/.zeromouse_state.json` |

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

## How It Works

- Fetches the product page HTML every `CHECK_INTERVAL` seconds.
- If the text "Sold out" is **not found** on the page, it sends a push notification via [ntfy.sh](https://ntfy.sh).
- After sending a notification, it waits at least 1 hour before sending another (to avoid spam).
- The last notification timestamp is persisted to `STATE_FILE`, so restarts keep cooldown behavior.
- The container auto-restarts on failure thanks to `restart: unless-stopped`.
- No passwords or API keys are needed — just a topic name.
