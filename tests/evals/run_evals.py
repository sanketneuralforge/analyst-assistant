# tests/evals/run_evals.py

"""
Run with: uv run python tests/evals/run_evals.py
Produces a summary report of all eval results.
"""

import subprocess
import sys
import json
from datetime import datetime


def run_evals():
    print("\n" + "="*60)
    print("  ANALYST ASSISTANT — EVAL HARNESS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    result = subprocess.run(
        ["uv", "run", "pytest", "tests/evals/", "-v",
         "--tb=short", "--no-header",
         "--json-report", "--json-report-file=tests/evals/last_run.json"],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:500])

    # Summary
    try:
        with open("tests/evals/last_run.json") as f:
            report = json.load(f)

        summary = report.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        total = summary.get("total", 0)
        duration = report.get("duration", 0)

        print("\n" + "="*60)
        print("  EVAL SUMMARY")
        print("="*60)
        print(f"  Passed:   {passed}/{total}")
        print(f"  Failed:   {failed}/{total}")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Score:    {passed/total*100:.0f}%" if total > 0 else "  Score: N/A")

        if failed == 0:
            print("\n  ✅ ALL EVALS PASSING")
        else:
            print(f"\n  ❌ {failed} EVAL(S) FAILING — check output above")
        print("="*60 + "\n")

    except FileNotFoundError:
        print("Note: install pytest-json-report for summary: uv add pytest-json-report")


if __name__ == "__main__":
    run_evals()