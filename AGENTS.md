# Agent Handoff — Zeromouse Monitor

## What this is

Simple stock availability monitor for zeromouse.co/products/blade. Polls the product page every 15 minutes (configurable), sends ntfy push notification when "Sold out" text disappears. 1-hour cooldown prevents spam. State persisted to disk for restart safety.

## Read order

1. `README.md` — setup, env vars, Docker run commands
2. `monitor.py` — everything is in one file

## Architecture

```
monitor.py → fetch page HTML → check for "Sold out" → send ntfy if not found → sleep CHECK_INTERVAL
           → persist last_notified timestamp to STATE_FILE
```

## Key constraints

- Single-file service — keep it that way; no abstraction needed
- State file path (`data/.zeromouse_state.json`) is mounted as a volume — persists across container restarts
- `--test` flag sends a test notification without checking availability — use this to verify ntfy before deploying
- Cooldown is hardcoded at 1 hour; adjust in `monitor.py` if needed
- NTFY_TOPIC must exactly match what's subscribed in the ntfy app

## Run commands

```bash
# Test notification
docker compose run --rm monitor python monitor.py --test

# Start daemon
docker compose up -d
docker compose logs -f

# Stop
docker compose down
```
