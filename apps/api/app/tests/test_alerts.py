"""Proactive alerts: emerging-problem Slack pings + scheduled weekly digest."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore
from app.services.alerts import run_alert_sweep
from app.services.telemetry import SQLiteTelemetryStore

SLACK = ConnectorConfig(
    connector_type="slack", config={"bot_token": "xoxb-1", "channel": "#alerts"}
)


def _item(title: str, *, label: str = "action") -> SimpleNamespace:
    return SimpleNamespace(
        title=title, journey="checkout", journey_stage="payment",
        trend_label=label, emerging_score=0.71, signal_count=3,
        customer_count=3, source_count=2,
    )


def _report(*items: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(signals=list(items))


class Recorder:
    def __init__(self) -> None:
        self.posts: list[str] = []

    def __call__(self, title: str, description: str, config: dict) -> None:
        self.posts.append(title)


def _sweep(tmp_path: Path, *, report, configs, push, telemetry=None, now=None):
    telemetry = telemetry or SQLiteTelemetryStore(tmp_path / "t.db")
    return telemetry, run_alert_sweep(
        emerging_report=report,
        connector_config_store=ConnectorConfigStore(configs),
        telemetry=telemetry,
        push_slack=push,
        build_digest_text=lambda: "digest body",
        now=now,
    )


def test_action_items_alert_once_and_digest_sends(tmp_path: Path) -> None:
    push = Recorder()
    telemetry, result = _sweep(
        tmp_path, report=_report(_item("Payment failures spiking")), configs=[SLACK], push=push
    )
    assert result == {"alerted": 1, "loop_alerted": 0, "digest_sent": 1}
    assert push.posts == ["CLARA: emerging problem needs attention", "CLARA weekly digest"]

    # Second sweep same day: the alert is deduped AND the digest is not resent.
    second = run_alert_sweep(
        emerging_report=_report(_item("Payment failures spiking")),
        connector_config_store=ConnectorConfigStore([SLACK]),
        telemetry=telemetry,
        push_slack=push,
        build_digest_text=lambda: "digest body",
    )
    assert second == {"alerted": 0, "loop_alerted": 0, "digest_sent": 0}
    assert len(push.posts) == 2


def test_watch_items_do_not_alert(tmp_path: Path) -> None:
    push = Recorder()
    _, result = _sweep(
        tmp_path, report=_report(_item("Mild grumbling", label="watch")), configs=[SLACK], push=push
    )
    assert result["alerted"] == 0


def test_no_slack_config_is_a_noop(tmp_path: Path) -> None:
    push = Recorder()
    _, result = _sweep(tmp_path, report=_report(_item("X")), configs=[], push=push)
    assert result == {"alerted": 0, "loop_alerted": 0, "digest_sent": 0}
    assert push.posts == []


def test_digest_weekly_gate(tmp_path: Path) -> None:
    push = Recorder()
    telemetry = SQLiteTelemetryStore(tmp_path / "t.db")
    telemetry.record("digest_sent", metadata={})  # sent just now
    _, result = _sweep(
        tmp_path, report=_report(), configs=[SLACK], push=push, telemetry=telemetry
    )
    assert result["digest_sent"] == 0

    # A week later the gate opens.
    later = run_alert_sweep(
        emerging_report=_report(),
        connector_config_store=ConnectorConfigStore([SLACK]),
        telemetry=telemetry,
        push_slack=push,
        build_digest_text=lambda: "digest body",
        now=datetime.now(timezone.utc) + timedelta(days=7),
    )
    assert later["digest_sent"] == 1


def test_failed_post_does_not_mark_alerted(tmp_path: Path) -> None:
    def failing_push(title: str, description: str, config: dict) -> None:
        raise RuntimeError("slack down")

    telemetry, result = _sweep(
        tmp_path, report=_report(_item("Broken checkout")), configs=[SLACK], push=failing_push
    )
    assert result == {"alerted": 0, "loop_alerted": 0, "digest_sent": 0}
    # Not marked: the next sweep with a healthy Slack must retry the alert.
    ok = Recorder()
    retry = run_alert_sweep(
        emerging_report=_report(_item("Broken checkout")),
        connector_config_store=ConnectorConfigStore([SLACK]),
        telemetry=telemetry,
        push_slack=ok,
        build_digest_text=lambda: "digest body",
    )
    assert retry["alerted"] == 1
