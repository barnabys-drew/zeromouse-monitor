import argparse
import json
import os
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

PRODUCT_URL = "https://zeromouse.co/products/blade"
PRODUCT_JSON_URL = "https://zeromouse.co/products/blade.json"

NTFY_TOPIC = os.environ["NTFY_TOPIC"]
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "900"))
NOTIFICATION_COOLDOWN = 3600  # re-notify at most once per hour
STATE_FILE = Path(os.environ.get("STATE_FILE", "data/.zeromouse_state.json"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("zeromouse-monitor")


def load_last_notified() -> float:
    """Restore last notification timestamp from disk when present."""
    try:
        if not STATE_FILE.exists():
            return 0.0
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return float(payload.get("last_notified", 0.0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0.0


def save_last_notified(last_notified: float) -> None:
    """Persist last notification timestamp for restart-safe cooldown."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(
            json.dumps({"last_notified": last_notified, "updated_at": time.time()}),
            encoding="utf-8",
        )
    except OSError:
        return


def fetch_availability() -> bool:
    """Return True if any variant is available. Uses Shopify JSON endpoint."""
    resp = requests.get(PRODUCT_JSON_URL, timeout=30)
    resp.raise_for_status()
    product = resp.json().get("product", {})
    variants = product.get("variants", [])
    if not variants:
        raise ValueError("No variants found in product JSON — page structure may have changed")
    return any(v.get("available") for v in variants)


def send_notification(title: str, body: str) -> None:
    requests.post(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "urgent",
            "Tags": "mouse,rotating_light",
            "Content-Type": "text/plain; charset=utf-8",
        },
        timeout=10,
    ).raise_for_status()
    log.info("Notification sent to %s/%s", NTFY_SERVER, NTFY_TOPIC)


def test_notification() -> None:
    """Send a test notification and exit."""
    log.info("Sending test notification to %s/%s ...", NTFY_SERVER, NTFY_TOPIC)
    send_notification(
        "Test - Zeromouse Monitor",
        "If you see this on your phone, ntfy is working!",
    )
    log.info("Done. Check your phone.")


def run_check_cycle(last_notified: float) -> float:
    """One fetch + optional notify. Returns updated last_notified timestamp."""
    try:
        available = fetch_availability()
        if not available:
            log.info("Still sold out.")
        else:
            log.info("*** AVAILABLE! The Blade appears to be in stock! ***")
            now = time.time()
            if now - last_notified >= NOTIFICATION_COOLDOWN:
                send_notification(
                    "Zeromouse Blade IN STOCK",
                    f"The Zeromouse Blade is IN STOCK!\n"
                    f"{PRODUCT_URL}\n\n"
                    f"Checked at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                )
                save_last_notified(now)
                return now
            log.info("Notification cooldown active — skipping.")
    except requests.RequestException as exc:
        log.error("Request failed: %s", exc)
    except ValueError as exc:
        log.error("Unexpected product structure: %s", exc)
    except Exception as exc:
        log.error("Unexpected error: %s", exc)
    return last_notified


def main() -> None:
    parser = argparse.ArgumentParser(description="Zeromouse Blade stock monitor")
    parser.add_argument("--test", action="store_true", help="Send a test notification and exit")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check and exit (for cron / hourly Docker runs)",
    )
    args = parser.parse_args()

    if args.test:
        test_notification()
        return

    log.info("Starting monitor for %s", PRODUCT_URL)
    if args.once:
        log.info("Single run (--once); exiting after one check.")
    else:
        log.info("Checking every %d seconds (%d minutes)", CHECK_INTERVAL, CHECK_INTERVAL // 60)
    log.info("Notifications via %s/%s", NTFY_SERVER, NTFY_TOPIC)

    last_notified = load_last_notified()
    if last_notified > 0:
        elapsed = max(0, time.time() - last_notified)
        log.info("Restored previous notification state (%.0fs ago).", elapsed)
    last_notified = run_check_cycle(last_notified)
    if args.once:
        return

    while True:
        time.sleep(CHECK_INTERVAL)
        last_notified = run_check_cycle(last_notified)


if __name__ == "__main__":
    main()
