import argparse
import json
import os
import sys
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

PRODUCT_URL = "https://zeromouse.co/products/blade"
PRODUCT_JSON_URL = "https://zeromouse.co/products/blade.json"
USER_AGENT = "zeromouse-monitor/1.0 (+https://github.com/barnabys-drew/zeromouse-monitor)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("zeromouse-monitor")


@dataclass
class Config:
    ntfy_topic: str
    ntfy_server: str = "https://ntfy.sh"
    check_interval: int = 900
    notify_cooldown: int = 3600
    failure_alert_threshold: int = 8
    state_file: Path = field(default_factory=lambda: Path("data/.zeromouse_state.json"))


def load_config() -> Config:
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        log.error("NTFY_TOPIC is not set — copy .env.example to .env and set a topic.")
        sys.exit(2)
    return Config(
        ntfy_topic=topic,
        ntfy_server=os.environ.get("NTFY_SERVER", "https://ntfy.sh"),
        check_interval=int(os.environ.get("CHECK_INTERVAL", "900")),
        notify_cooldown=int(os.environ.get("NOTIFY_COOLDOWN", "3600")),
        failure_alert_threshold=int(os.environ.get("FAILURE_ALERT_THRESHOLD", "8")),
        state_file=Path(os.environ.get("STATE_FILE", "data/.zeromouse_state.json")),
    )


def load_last_notified(state_file: Path) -> float:
    """Restore last notification timestamp from disk when present."""
    try:
        if not state_file.exists():
            return 0.0
        payload = json.loads(state_file.read_text(encoding="utf-8"))
        return float(payload.get("last_notified", 0.0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0.0


def save_last_notified(state_file: Path, last_notified: float) -> None:
    """Persist last notification timestamp for restart-safe cooldown."""
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            json.dumps({"last_notified": last_notified, "updated_at": time.time()}),
            encoding="utf-8",
        )
    except OSError:
        return


def fetch_availability() -> bool:
    """Return True if any variant is available. Uses Shopify JSON endpoint."""
    resp = requests.get(
        PRODUCT_JSON_URL, timeout=30, headers={"User-Agent": USER_AGENT}
    )
    resp.raise_for_status()
    product = resp.json().get("product", {})
    variants = product.get("variants", [])
    if not variants:
        raise ValueError("No variants found in product JSON — page structure may have changed")
    return any(v.get("available") for v in variants)


def send_notification(
    cfg: Config,
    title: str,
    body: str,
    priority: str = "urgent",
    tags: str = "mouse,rotating_light",
) -> None:
    requests.post(
        f"{cfg.ntfy_server}/{cfg.ntfy_topic}",
        data=body.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": priority,
            "Tags": tags,
            "Click": PRODUCT_URL,
            "Content-Type": "text/plain; charset=utf-8",
        },
        timeout=10,
    ).raise_for_status()
    log.info("Notification sent to %s/%s", cfg.ntfy_server, cfg.ntfy_topic)


def test_notification(cfg: Config) -> None:
    """Send a test notification and exit."""
    log.info("Sending test notification to %s/%s ...", cfg.ntfy_server, cfg.ntfy_topic)
    send_notification(
        cfg,
        "Test - Zeromouse Monitor",
        "If you see this on your phone, ntfy is working!",
    )
    log.info("Done. Check your phone.")


def run_check_cycle(cfg: Config, state: dict) -> None:
    """One fetch + optional notify. Mutates state in place.

    state keys: last_notified (float), failure_streak (int), failure_alerted (bool).
    """
    try:
        available = fetch_availability()
    except Exception as exc:
        if isinstance(exc, requests.RequestException):
            log.error("Request failed: %s", exc)
        elif isinstance(exc, ValueError):
            log.error("Unexpected product structure: %s", exc)
        else:
            log.error("Unexpected error: %s", exc)
        state["failure_streak"] += 1
        if (
            state["failure_streak"] >= cfg.failure_alert_threshold
            and not state["failure_alerted"]
        ):
            state["failure_alerted"] = True
            try:
                send_notification(
                    cfg,
                    "Zeromouse Monitor is failing",
                    f"{state['failure_streak']} consecutive checks have failed.\n"
                    f"Last error: {exc}",
                    priority="default",
                    tags="warning",
                )
            except requests.RequestException as alert_exc:
                log.error("Failure alert could not be sent: %s", alert_exc)
        return

    if state["failure_alerted"]:
        log.info("Checks recovered after %d failures.", state["failure_streak"])
    state["failure_streak"] = 0
    state["failure_alerted"] = False

    if not available:
        log.info("Still sold out.")
        return

    log.info("*** AVAILABLE! The Blade appears to be in stock! ***")
    now = time.time()
    if now - state["last_notified"] < cfg.notify_cooldown:
        log.info("Notification cooldown active — skipping.")
        return
    try:
        send_notification(
            cfg,
            "Zeromouse Blade IN STOCK",
            f"The Zeromouse Blade is IN STOCK!\n"
            f"{PRODUCT_URL}\n\n"
            f"Checked at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        )
    except requests.RequestException as exc:
        log.error("Notification failed: %s", exc)
        return
    state["last_notified"] = now
    save_last_notified(cfg.state_file, now)


def main() -> None:
    parser = argparse.ArgumentParser(description="Zeromouse Blade stock monitor")
    parser.add_argument("--test", action="store_true", help="Send a test notification and exit")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check and exit (for cron / hourly Docker runs)",
    )
    args = parser.parse_args()

    cfg = load_config()

    if args.test:
        test_notification(cfg)
        return

    log.info("Starting monitor for %s", PRODUCT_URL)
    if args.once:
        log.info("Single run (--once); exiting after one check.")
    else:
        log.info(
            "Checking every %d seconds (%d minutes)",
            cfg.check_interval,
            cfg.check_interval // 60,
        )
    log.info("Notifications via %s/%s", cfg.ntfy_server, cfg.ntfy_topic)

    state = {
        "last_notified": load_last_notified(cfg.state_file),
        "failure_streak": 0,
        "failure_alerted": False,
    }
    if state["last_notified"] > 0:
        elapsed = max(0, time.time() - state["last_notified"])
        log.info("Restored previous notification state (%.0fs ago).", elapsed)
    run_check_cycle(cfg, state)
    if args.once:
        return

    while True:
        time.sleep(cfg.check_interval)
        run_check_cycle(cfg, state)


if __name__ == "__main__":
    main()
