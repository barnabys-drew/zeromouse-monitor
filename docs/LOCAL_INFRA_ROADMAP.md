# Local infrastructure roadmap (homelab)

This note captures the **intended deployment story** for this project and related containers under `~/code` (**zeromouse-monitor**, **concentration-manager**, **catastrophe-analyzer**). The same file (with repo-specific links) lives in each of those repositories. It is **not** a hard requirement to run Zeromouse Monitor.

## Goals (in order)

1. **Checks and notifications work locally** — ntfy topic, `CHECK_INTERVAL` or `--once` cron runs, and logs behave as expected before investing in heavier hosting.
2. **Run everything on a dedicated spare PC** — quiet, always-on machine that can host Docker workloads, cron schedules, and logs.
3. **Hardware profile** — NVIDIA **RTX 3060 Ti**, a **capable AMD CPU**, and **plenty of RAM** so the same box can comfortably run:
   - scheduled **one-shot** containers (e.g. hourly `monitor.py --once`) or **long-running** `docker compose up`,
   - other **~/code** tools side by side (stock signals, news pipeline, etc.),
   - optional **local LLM** workloads on the same machine for sibling projects that need inference.
4. **Observability later** — if desired, add **Grafana** and/or **ELK/OpenSearch** (or cloud equivalents) for centralized dashboards and log search; whether that stays on the spare PC or moves to **GCP/AWS** is a separate decision.

## Design implication

- This monitor is **not LLM-based**; it stays lightweight (HTTP check + ntfy). It benefits from the same homelab logging and scheduling patterns as the other tools.

## Related files in this repo

- [README.md](../README.md) — Docker, ntfy, `CHECK_INTERVAL`, `--once` for cron  
- Shared hourly cron template (sibling path): `~/code/hourly-checks.crontab.example`

## Tailscale + ntfy on the homelab

Keep **`NTFY_TOPIC` in `.env`** and copy with **`tailscale file cp … chewbacca-1:`** (same as other env secrets). Full list: `../catastrophe-analyzer/docs/LOCAL_INFRA_ROADMAP.md`.

Update this file when the homelab hostname, IP, or “single compose stack” layout stabilizes.
