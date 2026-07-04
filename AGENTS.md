# Agent Handoff — Zeromouse Monitor

## What this is

Simple stock availability monitor for zeromouse.co/products/blade. Polls the Shopify product JSON endpoint every 15 minutes (configurable), sends ntfy push notification when any variant is available. Configurable cooldown prevents spam. State persisted to disk for restart safety. A watchdog sends a one-time "monitor is failing" alert after N consecutive failed checks.

## Read order

1. `README.md` — setup, env vars, Docker run commands
2. `monitor.py` — everything is in one file
3. `tests/test_monitor.py` — unit tests (pytest, mocked requests)

## Architecture

```
monitor.py → fetch /products/blade.json → any variant available? → send ntfy → sleep CHECK_INTERVAL
           → persist last_notified timestamp to STATE_FILE
           → on repeated failures (FAILURE_ALERT_THRESHOLD), send one-time watchdog alert
```

## Key constraints

- Single-file service — keep it that way; no abstraction needed. Tests live in `tests/`.
- Config is read in `load_config()` (called from `main()`), never at module import — `--help` and tests work without env vars
- State file path (`data/.zeromouse_state.json`) is mounted as a volume — persists across container restarts
- `--test` flag sends a test notification without checking availability — use this to verify ntfy before deploying
- Cooldown is `NOTIFY_COOLDOWN` (default 3600s); watchdog threshold is `FAILURE_ALERT_THRESHOLD` (default 8 checks)
- NTFY_TOPIC must exactly match what's subscribed in the ntfy app
- Container runs as non-root uid 1000 — must match the owner of the bind-mounted `./data`

## Run commands

```bash
# Unit tests
pip install -r requirements.txt pytest && pytest

# Test notification
docker compose run --rm monitor python monitor.py --test

# Start daemon
docker compose up -d
docker compose logs -f

# Stop
docker compose down
```
