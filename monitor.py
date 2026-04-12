import argparse
import os
import sys
import time
import logging
from datetime import datetime, timezone

import requests

PRODUCT_URL = "https://zeromouse.co/products/blade"
SOLD_OUT_MARKER = "Sold out"

NTFY_TOPIC = os.environ["NTFY_TOPIC"]
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "900"))
NOTIFICATION_COOLDOWN = 3600  # re-notify at most once per hour

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("zeromouse-monitor")


def fetch_page() -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(PRODUCT_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def is_sold_out(html: str) -> bool:
    return SOLD_OUT_MARKER in html


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
        html = fetch_page()
        if is_sold_out(html):
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
                return now
            log.info("Notification cooldown active — skipping.")
    except requests.RequestException as exc:
        log.error("Request failed: %s", exc)
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

    last_notified: float = 0.0
    last_notified = run_check_cycle(last_notified)
    if args.once:
        return

    while True:
        time.sleep(CHECK_INTERVAL)
        last_notified = run_check_cycle(last_notified)


if __name__ == "__main__":
    main()
