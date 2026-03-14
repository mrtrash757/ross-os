#!/usr/bin/env python3
"""
Ross OS — Email Monitor Runner
Combined orchestrator: runs email_classify_v3.py then create_email_tasks_v2.py,
reads their output files, composes a summary, and saves email_monitor_output.json.

Called by the Email Monitor cron (cron ID: 9342c183).
Schedule: 46 11,13,15,17,19,21,23 * * * → 7:46am, 9:46am, 11:46am, 1:46pm,
          3:46pm, 5:46pm, 7:46pm ET (7 runs/day)

Cron agent reads email_monitor_output.json to decide whether to send a notification.
Sends notification if High or Medium priority emails found.
"""

import json
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# ── Paths ──────────────────────────────────────────────────────────────────────
CLASSIFY_SCRIPT    = "/home/user/workspace/email_classify_v3.py"
TASK_SCRIPT        = "/home/user/workspace/create_email_tasks_v2.py"
CLASSIFY_OUTPUT    = "/home/user/workspace/email_classification_v3.json"
TASK_OUTPUT        = "/home/user/workspace/email_tasks_output.json"
MONITOR_OUTPUT     = "/home/user/workspace/email_monitor_output.json"

TZ = ZoneInfo("America/Detroit")


def now_et() -> str:
    """Return current timestamp as ISO string in ET."""
    return datetime.now(tz=TZ).isoformat()


def run_script(script_path: str) -> dict:
    """
    Run a Python script via subprocess.
    Returns a dict with keys: returncode, stdout, stderr, success.
    """
    print(f"▶  Running {script_path.split('/')[-1]} ...")
    result = subprocess.run(
        ["python3", script_path],
        capture_output=True,
        text=True,
    )
    success = result.returncode == 0
    status_icon = "✅" if success else "❌"
    print(f"{status_icon} {script_path.split('/')[-1]} exited with code {result.returncode}")
    if result.stdout:
        # Print each line of the child script's stdout, indented
        for line in result.stdout.strip().splitlines():
            print(f"   {line}")
    if result.stderr:
        print(f"   [STDERR] {result.stderr.strip()[:500]}")
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": success,
    }


def read_json(path: str) -> dict | None:
    """Read a JSON file, return None on any failure."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Output file not found: {path}")
        return None
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parse error in {path}: {e}")
        return None


def parse_classification(data: dict | None) -> tuple[dict, list[str]]:
    """
    Extract summary counts from email_classification_v3.json.
    Returns (summary_dict, errors_list).
    """
    errors = []
    if data is None:
        errors.append("Classification output file missing or unreadable")
        return {"total": 0, "high": 0, "medium": 0, "low": 0, "tasks_needed": 0}, errors

    results = data.get("results", [])
    total   = data.get("total", len(results))

    # Count by priority (only active emails — exclude archive)
    high   = sum(1 for r in results if r.get("priority") == "High"   and r.get("intent") != "archive")
    medium = sum(1 for r in results if r.get("priority") == "Medium" and r.get("intent") != "archive")
    low    = sum(1 for r in results if r.get("priority") == "Low"    and r.get("intent") != "archive")

    tasks_needed = sum(1 for r in results if r.get("needs_task") and r.get("intent") != "archive")

    summary = {
        "total": total,
        "high": high,
        "medium": medium,
        "low": low,
        "tasks_needed": tasks_needed,
    }
    return summary, errors


def parse_tasks(data: dict | None) -> tuple[dict, list[str]]:
    """
    Extract summary counts from email_tasks_output.json.
    Returns (summary_dict, errors_list).
    """
    errors = []
    if data is None:
        errors.append("Task output file missing or unreadable")
        return {"created": 0, "skipped": 0, "errors": []}, errors

    summary = {
        "created": data.get("created", 0),
        "skipped": data.get("skipped", 0),
        "errors":  data.get("errors", []),
    }
    return summary, errors


def print_summary(classification: dict, tasks: dict) -> None:
    """Print a human-readable summary to stdout."""
    total = classification["total"]
    high  = classification["high"]
    med   = classification["medium"]
    low   = classification["low"]
    tasks_needed = classification["tasks_needed"]
    created = tasks["created"]

    print()
    print("=" * 50)
    print("  📬 Email Monitor Summary")
    print("=" * 50)
    if total == 0:
        print("  Inbox empty — no emails to process.")
    else:
        print(f"  Total emails:   {total}")
        print(f"  🔴 High:        {high}")
        print(f"  🟡 Medium:      {med}")
        print(f"  🟢 Low:         {low}")
        print(f"  Tasks needed:   {tasks_needed}")
        print(f"  Tasks created:  {created}")
        if tasks["skipped"]:
            print(f"  Tasks skipped:  {tasks['skipped']}")
        if tasks["errors"]:
            print(f"  Task errors:    {len(tasks['errors'])}")
    print("=" * 50)
    print()


def main():
    timestamp = now_et()
    all_errors = []
    overall_status = "success"

    print(f"🕐 Email Monitor starting at {timestamp}")
    print()

    # ── Step 1: Run classifier ─────────────────────────────────────────────────
    classify_run = run_script(CLASSIFY_SCRIPT)

    if not classify_run["success"]:
        msg = (
            f"email_classify_v3.py failed (exit {classify_run['returncode']}): "
            f"{classify_run['stderr'].strip()[:300]}"
        )
        print(f"❌ {msg}")
        all_errors.append(msg)
        overall_status = "error"

        # Read whatever partial output exists (classifier may have written before failing)
        classify_data = read_json(CLASSIFY_OUTPUT)
    else:
        classify_data = read_json(CLASSIFY_OUTPUT)

    classification_summary, classify_errors = parse_classification(classify_data)
    all_errors.extend(classify_errors)

    # ── Early exit: empty inbox ────────────────────────────────────────────────
    if classification_summary["total"] == 0 and classify_run["success"]:
        print("📭 Inbox empty — no emails to classify. Exiting early.")
        output = {
            "timestamp": timestamp,
            "classification": classification_summary,
            "tasks": {"created": 0, "skipped": 0, "errors": []},
            "status": "success",
            "errors": [],
        }
        with open(MONITOR_OUTPUT, "w") as f:
            json.dump(output, f, indent=2)
        print(f"💾 Output saved to {MONITOR_OUTPUT}")
        return

    # ── Step 2: Run task creator (only if classifier didn't hard-fail) ─────────
    task_summary = {"created": 0, "skipped": 0, "errors": []}

    if classify_run["success"]:
        task_run = run_script(TASK_SCRIPT)

        if not task_run["success"]:
            msg = (
                f"create_email_tasks_v2.py failed (exit {task_run['returncode']}): "
                f"{task_run['stderr'].strip()[:300]}"
            )
            print(f"❌ {msg}")
            all_errors.append(msg)
            overall_status = "error"

        task_data = read_json(TASK_OUTPUT)
        task_summary, task_errors = parse_tasks(task_data)
        all_errors.extend(task_errors)
    else:
        print("⏭️  Skipping task creation — classifier did not succeed.")
        all_errors.append("Task creation skipped due to classifier failure")

    # ── Step 3: Print summary ──────────────────────────────────────────────────
    print_summary(classification_summary, task_summary)

    # Promote status to error if we have any errors accumulated
    if all_errors and overall_status != "error":
        overall_status = "error"

    # ── Step 4: Write combined output ─────────────────────────────────────────
    output = {
        "timestamp": timestamp,
        "classification": classification_summary,
        "tasks": task_summary,
        "status": overall_status,
        "errors": all_errors,
    }

    with open(MONITOR_OUTPUT, "w") as f:
        json.dump(output, f, indent=2)

    status_icon = "✅" if overall_status == "success" else "⚠️"
    print(f"{status_icon} Status: {overall_status}")
    print(f"💾 Output saved to {MONITOR_OUTPUT}")


if __name__ == "__main__":
    main()
