import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

import monitor
from monitor import Config


@pytest.fixture
def cfg(tmp_path):
    return Config(
        ntfy_topic="test-topic",
        notify_cooldown=3600,
        failure_alert_threshold=3,
        state_file=tmp_path / "state.json",
    )


@pytest.fixture
def state():
    return {"last_notified": 0.0, "failure_streak": 0, "failure_alerted": False}


def product_response(variants):
    resp = MagicMock()
    resp.json.return_value = {"product": {"variants": variants}}
    resp.raise_for_status.return_value = None
    return resp


class TestFetchAvailability:
    def test_available_when_any_variant_available(self, monkeypatch):
        monkeypatch.setattr(
            monitor.requests,
            "get",
            lambda *a, **k: product_response(
                [{"available": False}, {"available": True}]
            ),
        )
        assert monitor.fetch_availability() is True

    def test_sold_out_when_no_variant_available(self, monkeypatch):
        monkeypatch.setattr(
            monitor.requests,
            "get",
            lambda *a, **k: product_response([{"available": False}]),
        )
        assert monitor.fetch_availability() is False

    def test_empty_variants_raises(self, monkeypatch):
        monkeypatch.setattr(
            monitor.requests, "get", lambda *a, **k: product_response([])
        )
        with pytest.raises(ValueError):
            monitor.fetch_availability()

    def test_sends_user_agent(self, monkeypatch):
        captured = {}

        def fake_get(url, **kwargs):
            captured.update(kwargs)
            return product_response([{"available": True}])

        monkeypatch.setattr(monitor.requests, "get", fake_get)
        monitor.fetch_availability()
        assert captured["headers"]["User-Agent"] == monitor.USER_AGENT


class TestStatePersistence:
    def test_round_trip(self, tmp_path):
        state_file = tmp_path / "sub" / "state.json"
        monitor.save_last_notified(state_file, 1234.5)
        assert monitor.load_last_notified(state_file) == 1234.5

    def test_missing_file_returns_zero(self, tmp_path):
        assert monitor.load_last_notified(tmp_path / "nope.json") == 0.0

    def test_corrupt_file_returns_zero(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("not json")
        assert monitor.load_last_notified(state_file) == 0.0


class TestCooldown:
    def test_notifies_when_available(self, cfg, state, monkeypatch):
        monkeypatch.setattr(monitor, "fetch_availability", lambda: True)
        sent = []
        monkeypatch.setattr(
            monitor, "send_notification", lambda *a, **k: sent.append(a)
        )
        monitor.run_check_cycle(cfg, state)
        assert len(sent) == 1
        assert state["last_notified"] > 0
        assert monitor.load_last_notified(cfg.state_file) == state["last_notified"]

    def test_cooldown_suppresses_repeat(self, cfg, state, monkeypatch):
        monkeypatch.setattr(monitor, "fetch_availability", lambda: True)
        sent = []
        monkeypatch.setattr(
            monitor, "send_notification", lambda *a, **k: sent.append(a)
        )
        monitor.run_check_cycle(cfg, state)
        monitor.run_check_cycle(cfg, state)
        assert len(sent) == 1

    def test_notifies_again_after_cooldown(self, cfg, state, monkeypatch):
        monkeypatch.setattr(monitor, "fetch_availability", lambda: True)
        sent = []
        monkeypatch.setattr(
            monitor, "send_notification", lambda *a, **k: sent.append(a)
        )
        monitor.run_check_cycle(cfg, state)
        state["last_notified"] -= cfg.notify_cooldown + 1
        monitor.run_check_cycle(cfg, state)
        assert len(sent) == 2


class TestFailureAlert:
    def failing_fetch(self):
        raise requests.RequestException("boom")

    def test_alert_fires_once_at_threshold(self, cfg, state, monkeypatch):
        monkeypatch.setattr(monitor, "fetch_availability", self.failing_fetch)
        sent = []
        monkeypatch.setattr(
            monitor, "send_notification", lambda *a, **k: sent.append((a, k))
        )
        for _ in range(cfg.failure_alert_threshold + 2):
            monitor.run_check_cycle(cfg, state)
        assert len(sent) == 1
        assert sent[0][1]["priority"] == "default"

    def test_no_alert_below_threshold(self, cfg, state, monkeypatch):
        monkeypatch.setattr(monitor, "fetch_availability", self.failing_fetch)
        sent = []
        monkeypatch.setattr(
            monitor, "send_notification", lambda *a, **k: sent.append(a)
        )
        for _ in range(cfg.failure_alert_threshold - 1):
            monitor.run_check_cycle(cfg, state)
        assert sent == []

    def test_success_resets_streak_and_rearms_alert(self, cfg, state, monkeypatch):
        sent = []
        monkeypatch.setattr(
            monitor, "send_notification", lambda *a, **k: sent.append(a)
        )
        monkeypatch.setattr(monitor, "fetch_availability", self.failing_fetch)
        for _ in range(cfg.failure_alert_threshold):
            monitor.run_check_cycle(cfg, state)
        assert len(sent) == 1

        monkeypatch.setattr(monitor, "fetch_availability", lambda: False)
        monitor.run_check_cycle(cfg, state)
        assert state["failure_streak"] == 0
        assert state["failure_alerted"] is False

        monkeypatch.setattr(monitor, "fetch_availability", self.failing_fetch)
        for _ in range(cfg.failure_alert_threshold):
            monitor.run_check_cycle(cfg, state)
        assert len(sent) == 2


class TestConfig:
    def test_missing_topic_exits_cleanly(self, monkeypatch):
        monkeypatch.delenv("NTFY_TOPIC", raising=False)
        with pytest.raises(SystemExit) as excinfo:
            monitor.load_config()
        assert excinfo.value.code == 2

    def test_env_overrides(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NTFY_TOPIC", "my-topic")
        monkeypatch.setenv("NOTIFY_COOLDOWN", "60")
        monkeypatch.setenv("FAILURE_ALERT_THRESHOLD", "5")
        monkeypatch.setenv("STATE_FILE", str(tmp_path / "s.json"))
        cfg = monitor.load_config()
        assert cfg.ntfy_topic == "my-topic"
        assert cfg.notify_cooldown == 60
        assert cfg.failure_alert_threshold == 5
        assert cfg.state_file == tmp_path / "s.json"
