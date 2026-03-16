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
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ── Paths ──────────────────────────────────────────────────────────────────────
CLASSIFY_SCRIPT    = "/home/user/workspace/email_classify_v3.py"
TASK_SCRIPT        = "/home/user/workspace/create_email_tasks_v2.py"
CLASSIFY_OUTPUT    = "/home/user/workspace/email_classification_v3.json"
TASK_OUTPUT        = "/home/user/workspace/email_tasks_output.json"
MONITOR_OUTPUT     = "/home/user/workspace/email_monitor_output.json"

TZ = ZoneInfo("America/Detroit")

# ── Coda credentials (for auto-close sweep) ────────────────────────────────────
CODA_TOKEN = "f8b53a89-6376-486e-85d8-f59fffed59d1"
CODA_DOC   = "nSMMjxb_b2"
EMAIL_TASKS_TABLE = "grid-7IWNsZiHzE"
GMAIL_TABLE       = "grid-sync-1004-Email"
CODA_BASE  = f"https://coda.io/apis/v1/docs/{CODA_DOC}"
CODA_HEADERS = {
    "Authorization": f"Bearer {CODA_TOKEN}",
    "Content-Type": "application/json",
}


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


# ── Days table helpers ────────────────────────────────────────────────────────
DAYS_TABLE = "grid-Zm8ylxf9zc"
PERSONAL_TASKS_TABLE = "grid-G1O2W471aC"


# ── Habit Count/Streak updater ────────────────────────────────────────────────
HABIT_LOGS_TABLE = "grid-5FJBmY91ko"


def update_habit_counts() -> dict:
    """
    Recalculate Count and Streak for today's Habit Log rows.

    Count  = cumulative number of days the habit was completed (all time)
    Streak = consecutive completed days from most recent backwards
             (0 if today is uncompleted, even if yesterday was completed)

    Only writes to rows whose values actually changed.
    Returns {"updated": int, "checked": int}.
    """
    from collections import defaultdict

    print()
    print("🔢 Habit Count/Streak: recalculating today's logs...")

    today_str = datetime.now(tz=TZ).strftime("%Y-%m-%d")

    # 1. Fetch all Habit Log rows
    all_logs = coda_get_rows(HABIT_LOGS_TABLE)
    print(f"  Fetched {len(all_logs)} habit log rows")

    # 2. Group by habit name, noting today's row IDs
    habit_entries = defaultdict(list)  # habit_name → [{date, completed, row_id}]
    today_rows = {}  # habit_name → {row_id, current_count, current_streak}

    for log in all_logs:
        v = log.get("values", {})
        habit_name = str(v.get("Habit", "")).strip()
        raw_date = str(v.get("Date", "")).strip()
        date_str = raw_date[:10] if raw_date else ""
        completed = v.get("Completed?", False) is True

        if not habit_name or not date_str:
            continue

        habit_entries[habit_name].append({
            "date": date_str,
            "completed": completed,
        })

        if date_str == today_str:
            # Read existing Count/Streak from the row
            existing_count = v.get("Count")
            existing_streak = v.get("Streak")
            # Normalize: empty/null → None
            if existing_count in ("", None):
                existing_count = None
            else:
                try:
                    existing_count = int(float(existing_count))
                except (ValueError, TypeError):
                    existing_count = None
            if existing_streak in ("", None):
                existing_streak = None
            else:
                try:
                    existing_streak = int(float(existing_streak))
                except (ValueError, TypeError):
                    existing_streak = None

            today_rows[habit_name] = {
                "row_id": log["id"],
                "current_count": existing_count,
                "current_streak": existing_streak,
            }

    if not today_rows:
        print("  No habit logs found for today — nothing to update.")
        return {"updated": 0, "checked": 0}

    # 3. For each habit with a today row, recalculate Count and Streak
    updated = 0
    checked = 0

    for habit_name, today_info in today_rows.items():
        entries = sorted(habit_entries.get(habit_name, []), key=lambda x: x["date"])
        checked += 1

        # Count = total completed days
        correct_count = sum(1 for e in entries if e["completed"])

        # Streak = consecutive completed days from the end (most recent first)
        correct_streak = 0
        for e in reversed(entries):
            if e["completed"]:
                correct_streak += 1
            else:
                break

        # Only update if values differ
        if (today_info["current_count"] == correct_count
                and today_info["current_streak"] == correct_streak):
            continue

        success = coda_update_row(
            HABIT_LOGS_TABLE,
            today_info["row_id"],
            [
                {"column": "Count", "value": correct_count},
                {"column": "Streak", "value": correct_streak},
            ],
        )
        if success:
            updated += 1
            print(f"  ✅ {habit_name}: count={correct_count}, streak={correct_streak}")
        else:
            print(f"  ❌ {habit_name}: failed to update")

    if updated == 0:
        print(f"  ✅ All {checked} habits already have correct counts.")
    else:
        print(f"  🔢 Updated {updated}/{checked} habit logs")

    return {"updated": updated, "checked": checked}


# ── Sleep/Energy reply parser ─────────────────────────────────────────────────

def parse_sleep_energy_reply() -> dict:
    """
    Check the Gmail sync table for replies to the Morning Brief email
    that contain Sleep/Energy data. Parse and write to the Day row.

    Returns dict with parsed values or empty dict if nothing found.
    """
    import re as _re

    print()
    print("💤 Sleep/Energy: checking for Morning Brief replies...")

    today_str = datetime.now(tz=TZ).strftime("%Y-%m-%d")

    # 1. Get Gmail sync table rows
    gmail_rows = coda_get_rows(GMAIL_TABLE)

    # 2. Find replies to Morning Brief from Ross today
    candidates = []
    for r in gmail_rows:
        v = r.get("values", {})
        sender = str(v.get("From", "")).lower()
        subject = str(v.get("Subject", "")).lower()
        date = str(v.get("Date", ""))
        body = str(v.get("Text", ""))

        # Must be from Ross, subject contains morning brief, sent today
        if ("ross" in sender
            and ("morning brief" in subject or ("re:" in subject and "brief" in subject))
            and today_str in date):
            candidates.append({"body": body, "date": date})

    if not candidates:
        print("  No Morning Brief replies found today.")
        return {}

    # Sort by date descending, use the most recent reply
    candidates.sort(key=lambda x: x["date"], reverse=True)
    reply_body = candidates[0]["body"]
    print(f"  Found reply ({len(candidates)} total), parsing...")

    # 3. Parse Sleep and Energy from the reply
    result = {}

    # Sleep: match patterns like "Sleep: 7h", "sleep: 7.5 hours", "sleep 7h", "Sleep: 7"
    sleep_match = _re.search(
        r'sleep[:\s]+([\d.]+)\s*(h(?:ours?)?|hrs?)?',
        reply_body, _re.IGNORECASE
    )
    if sleep_match:
        result["sleep"] = sleep_match.group(1) + "h"

    # Energy: match "Energy: High", "energy high", "Energy: Med", etc.
    energy_match = _re.search(
        r'energy[:\s]+(low|medium|med|high)',
        reply_body, _re.IGNORECASE
    )
    if energy_match:
        raw = energy_match.group(1).strip().lower()
        energy_map = {"low": "Low", "medium": "Medium", "med": "Medium", "high": "High"}
        result["energy"] = energy_map.get(raw, "Medium")

    if not result:
        print("  Reply found but couldn\'t parse Sleep/Energy values.")
        return {}

    print(f"  Parsed: {result}")

    # 4. Find today's Day row and update
    day_rows = coda_get_rows(DAYS_TABLE)
    day_row_id = None
    for r in day_rows:
        if today_str in str(r.get("values", {}).get("Date", "")):
            day_row_id = r["id"]
            break

    if not day_row_id:
        print(f"  ⚠️  No Day row found for {today_str}")
        return result

    cells = []
    if "sleep" in result:
        cells.append({"column": "Sleep", "value": result["sleep"]})
    if "energy" in result:
        cells.append({"column": "Energy", "value": result["energy"]})

    if cells:
        success = coda_update_row(DAYS_TABLE, day_row_id, cells)
        if success:
            print(f"  ✅ Day row updated: {result}")
        else:
            print(f"  ❌ Failed to update Day row")

    return result


# ── Completion date stamp sweep ───────────────────────────────────────────────

def stamp_completion_dates() -> int:
    """
    Find tasks with Status=Done but no completion date, and stamp today's date.
    Covers both Personal Tasks (Completed at) and Email Tasks (Date Completed).
    Returns total tasks stamped.
    """
    print()
    print("📅 Completion date sweep: stamping Done tasks missing dates...")
    today_str = datetime.now(tz=TZ).strftime("%Y-%m-%d")
    stamped = 0

    # Personal Tasks: Status=Done, Completed at is empty
    personal_rows = coda_get_rows(PERSONAL_TASKS_TABLE)
    for r in personal_rows:
        v = r.get("values", {})
        status = str(v.get("Status", "")).strip()
        completed_at = str(v.get("Completed at", "")).strip()
        if status == "Done" and not completed_at:
            name = str(v.get("Name", ""))[:60]
            success = coda_update_row(
                PERSONAL_TASKS_TABLE, r["id"],
                [{"column": "Completed at", "value": today_str}]
            )
            if success:
                stamped += 1
                print(f"  ✅ Stamped personal: {name}")

    # Email Tasks: Status=Done, Date Completed is empty
    email_rows = coda_get_rows(EMAIL_TASKS_TABLE)
    for r in email_rows:
        v = r.get("values", {})
        status = str(v.get("Status", "")).strip()
        date_completed = str(v.get("Date Completed", "")).strip()
        if status == "Done" and not date_completed:
            name = str(v.get("Name", ""))[:60]
            success = coda_update_row(
                EMAIL_TASKS_TABLE, r["id"],
                [{"column": "Date Completed", "value": today_str}]
            )
            if success:
                stamped += 1
                print(f"  ✅ Stamped email: {name}")

    if stamped == 0:
        print("  ✅ All Done tasks already have completion dates.")
    else:
        print(f"  📅 Stamped {stamped} tasks with today\'s date")
    return stamped


# ── Auto-close sweep ────────────────────────────────────────────────────────────

def coda_get_rows(table_id: str, limit: int = 500) -> list[dict]:
    """Fetch all rows from a Coda table with pagination."""
    all_rows = []
    url = f"{CODA_BASE}/tables/{table_id}/rows"
    params = {"useColumnNames": "true", "limit": str(limit)}
    while url:
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=CODA_HEADERS, params=params, timeout=20)
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 5))
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    print(f"  ❌ Failed to fetch {table_id}: {e}")
                    return all_rows
        all_rows.extend(data.get("items", []))
        next_uri = data.get("nextPageLink")
        url = next_uri if next_uri else None
        params = {} if next_uri else params
    return all_rows


def coda_update_row(table_id: str, row_id: str, cells: list[dict]) -> bool:
    """Update a single Coda row. Returns True on success."""
    url = f"{CODA_BASE}/tables/{table_id}/rows/{row_id}"
    body = {"row": {"cells": cells}}
    for attempt in range(3):
        try:
            resp = requests.put(url, headers=CODA_HEADERS, json=body, timeout=15)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return True
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  ❌ Failed to update row {row_id}: {e}")
                return False
    return False


def _parse_due_date(raw: str) -> datetime | None:
    """Try to parse a due-date string into a datetime. Returns None on failure."""
    raw = str(raw).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=TZ)
        except ValueError:
            continue
    # Try ISO 8601
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def auto_close_sweep() -> int:
    """
    Check all Email Tasks with Status="Inbox".
    If the task's thread (Thread ID link) is no longer in the Gmail sync table,
    mark it Done — Ross already handled it.

    PROTECTION: Tasks with a due date in the past (overdue) are skipped.
    Ross keeps those intentionally as straggler reminders.

    Returns the number of tasks closed.
    """
    print()
    print("🧹 Auto-close sweep: checking for cleaned-out emails...")

    # 1. Get current Gmail inbox threads
    gmail_rows = coda_get_rows(GMAIL_TABLE)
    inbox_links = set()
    for r in gmail_rows:
        v = r.get("values", {})
        labels = str(v.get("Labels", ""))
        link = str(v.get("Link", "")).strip()
        if "INBOX" in labels and link:
            inbox_links.add(link)
    print(f"  📬 Current inbox threads: {len(inbox_links)}")

    # 2. Get all Email Tasks with Status=Inbox
    all_tasks = coda_get_rows(EMAIL_TASKS_TABLE)
    inbox_tasks = []
    for r in all_tasks:
        v = r.get("values", {})
        status = str(v.get("Status", "")).strip()
        if status == "Inbox":
            inbox_tasks.append(r)
    print(f"  📋 Open email tasks (Inbox): {len(inbox_tasks)}")

    if not inbox_tasks:
        print("  ✅ No open tasks to check.")
        return 0

    # 3. For each Inbox task, check if its thread is still in Gmail inbox
    today = datetime.now(tz=TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today.strftime("%Y-%m-%d")
    closed = 0
    skipped_overdue = 0
    for task in inbox_tasks:
        v = task.get("values", {})
        thread_link = str(v.get("Thread ID link", "")).strip()
        task_name = str(v.get("Name", ""))[:60]
        row_id = task.get("id", "")
        due_raw = v.get("Due date", "")

        # If the thread link is still in the inbox, skip
        if thread_link and thread_link in inbox_links:
            continue

        # PROTECTION: Skip overdue tasks — Ross is holding them intentionally
        due_dt = _parse_due_date(due_raw)
        if due_dt and due_dt < today:
            skipped_overdue += 1
            print(f"  📌 Kept (overdue hold): {task_name}  [due {due_raw}]")
            continue

        # Thread is gone from inbox — mark as Done
        success = coda_update_row(
            EMAIL_TASKS_TABLE,
            row_id,
            [
                {"column": "Status", "value": "Done"},
                {"column": "Date Completed", "value": today_str},
            ],
        )
        if success:
            closed += 1
            print(f"  ✅ Closed: {task_name}")
        else:
            print(f"  ❌ Failed to close: {task_name}")

    print(f"  🧹 Auto-closed {closed} tasks (threads no longer in inbox)")
    if skipped_overdue:
        print(f"  📌 Skipped {skipped_overdue} overdue tasks (intentional holds)")
    return closed


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

    # ── Step 2: Run task creator (skip if inbox empty or classifier failed) ────
    task_summary = {"created": 0, "skipped": 0, "errors": []}

    if classification_summary["total"] == 0 and classify_run["success"]:
        print("📭 Inbox empty — no new emails to classify.")
    elif classify_run["success"]:
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

    # ── Step 2.5: Auto-close sweep (ALWAYS runs, even on empty inbox) ─────────
    # If an email task's thread is no longer in the Gmail inbox, mark it Done.
    # Ross cleans his inbox — tasks for handled emails should auto-close.
    # Overdue tasks are protected (Ross holds them as intentional reminders).
    closed_count = auto_close_sweep()
    task_summary["auto_closed"] = closed_count

    # ── Step 2.6: Completion date stamp ────────────────────────────────────────
    # Stamp today's date on Done tasks that are missing a completion date.
    stamped_count = stamp_completion_dates()
    task_summary["completion_dates_stamped"] = stamped_count

    # ── Step 2.7: Sleep/Energy from Morning Brief reply ────────────────────────
    # Check if Ross replied to the morning brief with Sleep/Energy data.
    sleep_energy = parse_sleep_energy_reply()
    if sleep_energy:
        task_summary["sleep_energy_logged"] = sleep_energy

    # ── Step 2.8: Habit Count/Streak updater ──────────────────────────────────
    # Recalculate Count and Streak on today's habit logs.
    # Catches when Ross checks off a habit between monitor runs.
    habit_update = update_habit_counts()
    task_summary["habit_counts"] = habit_update

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
