#!/usr/bin/env python3
"""Check the status of crawl runs via the crawllmer API.

Usage:
    # Check all recent runs
    python scripts/check-crawl-status.py

    # Check a specific run
    python scripts/check-crawl-status.py <run-id>

    # Use a different API base URL
    CRAWLLMER_API=http://localhost:8000 python scripts/check-crawl-status.py

Exit codes:
    0 - all runs completed successfully
    1 - at least one run failed
    2 - at least one run still in progress
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API_BASE = os.environ.get("CRAWLLMER_API", "http://localhost:8000")


def api_get(path: str) -> dict | list | None:
    """Fetch JSON from the API."""
    try:
        req = urllib.request.Request(f"{API_BASE}{path}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError:
        return None
    except Exception as e:  # noqa: BLE001
        print(f"API error ({path}): {e}", file=sys.stderr)
        return None


def print_run(run: dict, *, verbose: bool = False) -> None:
    """Print a single run's status."""
    rid = run["run_id"]
    host = run.get("host", "?")
    status = run.get("status", "?")
    score = run.get("score")
    score_str = f"{score:.0%}" if score is not None else "--"

    icon = {"completed": "✓", "failed": "✗", "running": "▶", "queued": "○"}.get(
        status, "?"
    )

    print(f"  {icon}  {host:<35} {status:<12} {score_str}")

    if verbose and status == "failed":
        print("     Error: check events for details")

    if verbose:
        events = api_get(f"/api/v1/crawls/{rid}/events")
        if events:
            print(f"     Events: {len(events)}")
            # Show last 3 stage events
            stage_events = [e for e in events if e["name"].startswith("stage.")]
            for ev in stage_events[-5:]:
                dur = f"{int(ev['duration'] * 1000)}ms" if ev.get("duration") else "--"
                outcome = ev.get("metadata", {}).get("outcome", "?")
                print(f"       {ev['name']:<30} {dur:<10} {outcome}")


def main() -> None:
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if args:
        # Check specific run
        run_id = args[0]
        run = api_get(f"/api/v1/crawls/{run_id}")
        if run is None:
            print(f"Run {run_id} not found.")
            sys.exit(1)
        print(f"{'Host':<39} {'Status':<12} {'Score'}")
        print("-" * 60)
        print_run(
            {
                "run_id": run["run_id"],
                "host": run.get("run_id", "?"),
                "status": run["status"],
                "score": run.get("score"),
            },
            verbose=verbose,
        )
    else:
        # List all recent runs
        history = api_get("/api/v1/history")
        if history is None:
            print("Could not reach API. Is `make run-dev` running?")
            sys.exit(1)

        if not history:
            print("No crawl runs found.")
            sys.exit(0)

        print(f"{'Host':<39} {'Status':<12} {'Score'}")
        print("-" * 60)
        for run in history:
            print_run(run, verbose=verbose)

        # Summary
        total = len(history)
        completed = sum(1 for r in history if r["status"] == "completed")
        failed = sum(1 for r in history if r["status"] == "failed")
        running = sum(1 for r in history if r["status"] in ("running", "queued"))
        print(
            f"\n{completed}/{total} completed, {failed} failed, {running} in progress"
        )

        if failed:
            sys.exit(1)
        if running:
            sys.exit(2)


if __name__ == "__main__":
    main()
