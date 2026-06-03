# observability/metrics.py

"""
Production metrics derived from run traces.

These are the metrics you'd monitor in production:
- Task completion rate: what % of runs complete successfully
- Tool error rate: what % of mode calls fail
- Latency p50/p95: median and tail latency per mode
- Cost per run: estimated token cost
- Human intervention rate: how often Mode 4 returns UNSUPPORTED
"""

import sqlite3
import statistics
from pathlib import Path

DB_PATH = Path("db/traces.db")

# Groq pricing (per 1M tokens, approximate)
COST_PER_1M = {
    "llama-3.3-70b-versatile": 0.59,
    "llama-3.1-8b-instant": 0.05,
}


def get_production_metrics() -> dict:
    """
    Compute all production metrics from stored traces.
    Returns a dict suitable for dashboard display.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # ── Run-level metrics ────────────────────────────────────
        runs = conn.execute("SELECT * FROM runs").fetchall()
        if not runs:
            return _empty_metrics()

        total_runs = len(runs)
        completed = [r for r in runs if r["status"] == "success"]
        failed = [r for r in runs if r["status"] == "error"]
        completion_rate = len(completed) / total_runs * 100 if total_runs > 0 else 0

        # ── Span-level metrics ───────────────────────────────────
        spans = conn.execute("SELECT * FROM spans").fetchall()
        conn.close()

        total_spans = len(spans)
        failed_spans = [s for s in spans if s["status"] == "error"]
        error_rate = len(failed_spans) / total_spans * 100 if total_spans > 0 else 0

        # ── Latency per mode (p50 and p95) ───────────────────────
        mode_latencies = {}
        for span in spans:
            mode = span["mode"]
            ms = span["duration_ms"] or 0
            if mode not in mode_latencies:
                mode_latencies[mode] = []
            mode_latencies[mode].append(ms)

        latency_stats = {}
        for mode, latencies in mode_latencies.items():
            if latencies:
                sorted_l = sorted(latencies)
                n = len(sorted_l)
                p50 = sorted_l[int(n * 0.5)]
                p95 = sorted_l[int(n * 0.95)] if n >= 20 else sorted_l[-1]
                latency_stats[mode] = {
                    "p50_ms": p50,
                    "p95_ms": p95,
                    "count": n,
                    "avg_ms": int(sum(latencies) / n),
                }

        # ── Token and cost metrics ───────────────────────────────
        total_tokens = sum(
            (s["input_tokens"] or 0) + (s["output_tokens"] or 0)
            for s in spans
        )
        estimated_cost = sum(
            ((s["input_tokens"] or 0) + (s["output_tokens"] or 0)) / 1_000_000
            * COST_PER_1M.get(s["model"] or "", 0.59)
            for s in spans
        )
        avg_tokens_per_run = total_tokens / total_runs if total_runs > 0 else 0
        avg_cost_per_run = estimated_cost / total_runs if total_runs > 0 else 0

        # ── Model usage breakdown ────────────────────────────────
        model_counts = {}
        for span in spans:
            model = span["model"] or "unknown"
            model_counts[model] = model_counts.get(model, 0) + 1

        return {
            "total_runs": total_runs,
            "completion_rate": round(completion_rate, 1),
            "error_rate": round(error_rate, 1),
            "total_spans": total_spans,
            "failed_spans": len(failed_spans),
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 4),
            "avg_tokens_per_run": int(avg_tokens_per_run),
            "avg_cost_per_run": round(avg_cost_per_run, 4),
            "latency_stats": latency_stats,
            "model_counts": model_counts,
        }

    except Exception as e:
        return {**_empty_metrics(), "_error": str(e)}


def _empty_metrics() -> dict:
    return {
        "total_runs": 0,
        "completion_rate": 0,
        "error_rate": 0,
        "total_spans": 0,
        "failed_spans": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0,
        "avg_tokens_per_run": 0,
        "avg_cost_per_run": 0,
        "latency_stats": {},
        "model_counts": {},
    }