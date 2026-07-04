#!/usr/bin/env bash
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not reachable — is Docker Desktop / WSL integration running?" >&2
  exit 1
fi

existing_id="$(docker compose ps -q monitor 2>/dev/null || true)"
was_running=false
if [ -n "$existing_id" ] && [ "$(docker inspect -f '{{.State.Running}}' "$existing_id" 2>/dev/null || true)" = "true" ]; then
  was_running=true
fi

log="$(mktemp)"
trap 'rm -f "$log"' EXIT

if ! docker compose up -d --quiet-pull >"$log" 2>&1; then
  cat "$log" >&2
  exit 1
fi

if [ "$was_running" = true ]; then
  echo "zeromouse-monitor already running."
else
  echo "zeromouse-monitor started."
fi
