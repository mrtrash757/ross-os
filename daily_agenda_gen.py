#!/usr/bin/env python3
"""
Ross OS — Daily Agenda Generator
Called by the morning brief cron each day at 6:30am ET.

Creates:
1. Today's Day row (if missing)
2. Today's Habit Log rows (one per active habit, skips duplicates)
3. Today's Workout Instance rows (based on schedule matching DOW, skips duplicates)

Also returns a JSON summary used by the morning brief to compose its notification.
"""

import json
import sys
import os
import requests
from datetime import datetime, timezone, timedelta

# ── Config ──────────────────────────────────────────────────────────────
CODA_TOKEN = "f8b53a89-6376-486e-85d8-f59fffed59d1"
CODA_DOC = "nSMMjxb_b2"
CODA_BASE = f"https://coda.io/apis/v1/docs/{CODA_DOC}"
HEADERS = {
    "Authorization": f"Bearer {CODA_TOKEN}",
    "Content-Type": "application/json",
}

# Table IDs
DAYS_TABLE = "grid-Zm8ylxf9zc"
HABITS_TABLE = "grid-5WHcBsnbmk"
HABIT_LOGS_TABLE = "grid-5FJBmY91ko"
WORKOUTS_TABLE = "grid-kOoUMffFTS"
WORKOUT_INSTANCES_TABLE = "grid-vEv0-YZI9h"

# Timezone — auto-detect EST/EDT
def get_et_offset():
    """Return UTC offset for America/Detroit (ET)."""
    try:
        from zoneinfo import ZoneInfo
        import datetime as dt
        now = dt.datetime.now(ZoneInfo("America/Detroit"))
        return now.utcoffset()
    except Exception:
        # Fallback: EDT = -4
        return timedelta(hours=-4)

ET = timezone(get_et_offset())

# ── Helpers ─────────────────────────────────────────────────────────────
DOW_MAP = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}

def today_et():
    """Return today's date in ET as YYYY-MM-DD and DOW string."""
    now = datetime.now(ET)
    return now.strftime("%Y-%m-%d"), DOW_MAP[now.weekday()], now.strftime("%A")

def coda_get(table_id, params=None):
    """Fetch all rows from a Coda table (handles pagination)."""
    url = f"{CODA_BASE}/tables/{table_id}/rows"
    p = {"useColumnNames": "true", "limit": 500}
    if params:
        p.update(params)
    all_rows = []
    while url:
        resp = requests.get(url, headers=HEADERS, params=p)
        resp.raise_for_status()
        data = resp.json()
        all_rows.extend(data.get("items", []))
        next_uri = data.get("nextPageLink")
        if next_uri:
            url = next_uri
            p = {}  # pagination URL includes params
        else:
            url = None
    return all_rows

def coda_upsert(table_id, rows, key_columns=None):
    """Upsert rows to a Coda table. Handles rate limits."""
    import time
    url = f"{CODA_BASE}/tables/{table_id}/rows"
    body = {"rows": rows}
    if key_columns:
        body["keyColumns"] = key_columns
    for attempt in range(3):
        resp = requests.post(url, headers=HEADERS, json=body)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            print(f"   ⏳ Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()  # Final attempt raises
    return resp.json()

# ── Main Logic ──────────────────────────────────────────────────────────
def run():
    today, dow_short, dow_full = today_et()
    print(f"📅 Daily Agenda Gen — {dow_full}, {today}")
    
    results = {
        "date": today,
        "dow": dow_full,
        "day_row_created": False,
        "habits_created": 0,
        "habits_skipped": 0,
        "workouts_created": 0,
        "workouts_skipped": 0,
        "errors": [],
    }

    # ── 1. Ensure Day row exists ────────────────────────────────────
    print("\n1️⃣  Ensuring Day row exists...")
    try:
        day_rows = coda_get(DAYS_TABLE)
        day_exists = any(today in str(r.get("values", {}).get("Date", "")) for r in day_rows)
        
        if not day_exists:
            coda_upsert(DAYS_TABLE, [{"cells": [
                {"column": "Date", "value": today},
            ]}])
            results["day_row_created"] = True
            print(f"   ✅ Created Day row for {today}")
        else:
            print(f"   ⏭️  Day row already exists for {today}")
    except Exception as e:
        err = f"Day row: {e}"
        results["errors"].append(err)
        print(f"   ❌ {err}")

    # ── 2. Create Habit Logs ────────────────────────────────────────
    print("\n2️⃣  Creating Habit Logs...")
    try:
        # Get active habits
        all_habits = coda_get(HABITS_TABLE)
        active_habits = [
            r for r in all_habits
            if r.get("values", {}).get("Active?") is True
            and r.get("values", {}).get("Name", "").strip()
        ]
        print(f"   Found {len(active_habits)} active habits")

        # Get existing habit logs for today
        all_logs = coda_get(HABIT_LOGS_TABLE)
        today_log_habits = set()
        for log in all_logs:
            v = log.get("values", {})
            log_date = str(v.get("Date", ""))
            if today in log_date:
                today_log_habits.add(v.get("Habit", "").strip())

        print(f"   Existing logs for today: {len(today_log_habits)}")

        # Create missing habit logs
        new_logs = []
        for habit in active_habits:
            habit_name = habit["values"]["Name"].strip()
            if habit_name in today_log_habits:
                results["habits_skipped"] += 1
                continue
            
            new_logs.append({"cells": [
                {"column": "Name", "value": f"{habit_name} — {today}"},
                {"column": "Habit", "value": habit_name},
                {"column": "Date", "value": today},
                {"column": "Completed?", "value": False},
                {"column": "Day", "value": today},
            ]})

        if new_logs:
            coda_upsert(HABIT_LOGS_TABLE, new_logs)
            results["habits_created"] = len(new_logs)
            print(f"   ✅ Created {len(new_logs)} habit logs")
        else:
            print(f"   ⏭️  All habit logs already exist")

    except Exception as e:
        err = f"Habit logs: {e}"
        results["errors"].append(err)
        print(f"   ❌ {err}")

    # ── 3. Create Workout Instances ─────────────────────────────────
    print("\n3️⃣  Creating Workout Instances...")
    try:
        # Get workout schedules matching today's DOW
        all_schedules = coda_get(WORKOUTS_TABLE)
        today_schedules = [
            r for r in all_schedules
            if dow_short in str(r.get("values", {}).get("Default days", ""))
        ]
        print(f"   Found {len(today_schedules)} schedules for {dow_short}")

        # Get existing workout instances for today
        all_instances = coda_get(WORKOUT_INSTANCES_TABLE)
        today_instance_names = set()
        for inst in all_instances:
            v = inst.get("values", {})
            # Date is a formula from Days lookup, but Name includes the date
            name = str(v.get("Name", ""))
            if today in name:
                today_instance_names.add(name)

        print(f"   Existing instances for today: {len(today_instance_names)}")

        # Create missing workout instances
        new_instances = []
        for schedule in today_schedules:
            sched_name = schedule["values"]["Name"].strip()
            # Instance name format: "Category — YYYY-MM-DD" (e.g., "Bodyweight — Sun" → "Bodyweight — 2026-03-08")
            # Extract the category part before " — DOW"
            category = sched_name.rsplit(" — ", 1)[0] if " — " in sched_name else sched_name
            instance_name = f"{category} — {today}"
            
            if instance_name in today_instance_names:
                results["workouts_skipped"] += 1
                continue

            # Link to the Day row via the Days lookup column
            # The Days column expects the Day row's display value (the date)
            new_instances.append({"cells": [
                {"column": "Name", "value": instance_name},
                {"column": "Days", "value": today},
                {"column": "Completed?", "value": False},
            ]})
            # Also try to link Workout schedule
            # The Workout column is a lookup to Workouts table
            # Set it to the schedule row's display name
            sched_row_name = schedule.get("name", "")
            if sched_row_name:
                new_instances[-1]["cells"].append(
                    {"column": "Workout", "value": sched_row_name}
                )

        if new_instances:
            coda_upsert(WORKOUT_INSTANCES_TABLE, new_instances)
            results["workouts_created"] = len(new_instances)
            print(f"   ✅ Created {len(new_instances)} workout instances")
        else:
            print(f"   ⏭️  All workout instances already exist")

    except Exception as e:
        err = f"Workout instances: {e}"
        results["errors"].append(err)
        print(f"   ❌ {err}")

    # ── Summary ─────────────────────────────────────────────────────
    print(f"\n📊 Summary:")
    print(f"   Day row: {'Created' if results['day_row_created'] else 'Existed'}")
    print(f"   Habits: {results['habits_created']} created, {results['habits_skipped']} skipped")
    print(f"   Workouts: {results['workouts_created']} created, {results['workouts_skipped']} skipped")
    if results["errors"]:
        print(f"   ⚠️  Errors: {results['errors']}")

    # Save results
    out_path = "/home/user/workspace/daily_agenda_output.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to {out_path}")
    
    return results

if __name__ == "__main__":
    run()
