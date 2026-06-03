# observability/alerts.py

"""
Alert rules for production monitoring.

Each alert has a condition, a severity, and a message.
Alerts are evaluated against current metrics and displayed
in the observability dashboard.

In production you'd send these to Slack, PagerDuty, or email.
Here they render in the UI so you can see them during a demo.
"""

from dataclasses import dataclass


@dataclass
class Alert:
    name: str
    severity: str      # "critical" | "warning" | "info"
    message: str
    value: float
    threshold: float


def evaluate_alerts(metrics: dict) -> list[Alert]:
    """
    Evaluate all alert rules against current metrics.
    Returns list of triggered alerts.
    """
    alerts = []

    # ── Critical alerts ──────────────────────────────────────────
    if metrics["completion_rate"] < 70 and metrics["total_runs"] >= 5:
        alerts.append(Alert(
            name="Low Completion Rate",
            severity="critical",
            message=f"Task completion rate is {metrics['completion_rate']}% — below 70% threshold.",
            value=metrics["completion_rate"],
            threshold=70,
        ))

    if metrics["error_rate"] > 20 and metrics["total_spans"] >= 10:
        alerts.append(Alert(
            name="High Error Rate",
            severity="critical",
            message=f"Span error rate is {metrics['error_rate']}% — above 20% threshold.",
            value=metrics["error_rate"],
            threshold=20,
        ))

    # ── Warning alerts ───────────────────────────────────────────
    if metrics["avg_tokens_per_run"] > 15000:
        alerts.append(Alert(
            name="High Token Usage",
            severity="warning",
            message=f"Average {metrics['avg_tokens_per_run']:,} tokens per run — context trimming may be needed.",
            value=metrics["avg_tokens_per_run"],
            threshold=15000,
        ))

    if metrics["avg_cost_per_run"] > 0.05:
        alerts.append(Alert(
            name="High Cost Per Run",
            severity="warning",
            message=f"Average cost per run is ${metrics['avg_cost_per_run']:.4f} — review model routing.",
            value=metrics["avg_cost_per_run"],
            threshold=0.05,
        ))

    # Check p95 latency per mode
    for mode, stats in metrics.get("latency_stats", {}).items():
        if stats["p95_ms"] > 10000:
            alerts.append(Alert(
                name=f"High Latency — {mode}",
                severity="warning",
                message=f"{mode} p95 latency is {stats['p95_ms']}ms — above 10s threshold.",
                value=stats["p95_ms"],
                threshold=10000,
            ))

    # ── Info alerts ──────────────────────────────────────────────
    if metrics["total_runs"] == 0:
        alerts.append(Alert(
            name="No Runs Recorded",
            severity="info",
            message="No agent runs recorded yet. Run a mode to start collecting metrics.",
            value=0,
            threshold=0,
        ))

    return alerts