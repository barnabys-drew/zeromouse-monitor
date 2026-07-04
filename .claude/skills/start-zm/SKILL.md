---
name: start-zm
description: Start the zeromouse-monitor Docker stack (the Zeromouse Blade stock checker) if it isn't already running. Use whenever the user asks to start, launch, boot up, turn on, or make sure the zeromouse monitor is running, or types /start-zm.
---

# /start-zm — start zeromouse-monitor

Starts the `monitor` service defined in this repo's `docker-compose.yml`.

Run:

```bash
<skill-dir>/scripts/start.sh
```

The script is idempotent and safe to run any number of times:

- If the Docker daemon isn't reachable, it prints a one-line error and exits non-zero.
- If the container is already running, it silently confirms with `zeromouse-monitor already running.` — no error, no noise.
- Otherwise it runs `docker compose up -d` and reports `zeromouse-monitor started.`
- Real failures (bad `.env`, build errors, etc.) are surfaced by dumping the `docker compose up` output.

Just run the script and relay its one-line output (or the error) to the user — no further steps needed.
