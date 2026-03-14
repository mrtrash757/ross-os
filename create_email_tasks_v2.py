#!/usr/bin/env python3
"""
Ross OS — Create Email Tasks v2
Reads classification output from email_classify_v3.py and creates
Email-linked Task rows in Coda for emails that need tasks.

Input:  /home/user/workspace/email_classification_v3.json
Output: /home/user/workspace/email_tasks_output.json
"""

import json
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ── Credentials ─────────────────────────────────────────────────────
TOKEN = "f8b53a89-6376-486e-85d8-f59fffed59d1"
DOC   = "nSMMjxb_b2"

# ── Table IDs ────────────────────────────────────────────────────────
SETTINGS_TABLE    = "grid-ybi2tIogls"
EMAIL_TASKS_TABLE = "grid-7IWNsZiHzE"
CONTACTS_TABLE    = "grid-1M2UOaliIC"
PROJECTS_TABLE    = "grid-fRBsFa2OZx"

# ── Constants ────────────────────────────────────────────────────────
INPUT_FILE  = "/home/user/workspace/email_classification_v3.json"
OUTPUT_FILE = "/home/user/workspace/email_tasks_output.json"
DEFAULT_MAX_TASKS = 25
TZ = ZoneInfo("America/Detroit")

CODA_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


# ── Coda helpers ─────────────────────────────────────────────────────

def coda_get(table_id, limit=500):
    """Fetch all rows from a Coda table with pagination and 429 retry."""
    all_rows = []
    url = f"https://coda.io/apis/v1/docs/{DOC}/tables/{table_id}/rows"
    params = {"useColumnNames": "true", "limit": str(limit)}
    while url:
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=CODA_HEADERS, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 5))
                    print(f"  ⏳ Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < 2:
                    print(f"  ⚠️  Retry {attempt + 1} for {table_id}: {e}")
                    time.sleep(2)
                else:
                    print(f"  ❌ Failed to fetch {table_id} after 3 attempts: {e}")
                    return all_rows
        all_rows.extend(data.get("items", []))
        next_uri = data.get("nextPageLink")
        if next_uri:
            url = next_uri
            params = {}  # pagination URL already includes params
        else:
            url = None
    return all_rows


def coda_upsert(table_id, row_data):
    """
    Insert a new row into Coda.
    Returns True on success, False on failure.
    Uses keyColumns upsert — but since Thread ID link is the dedup key
    and we've already checked, this is effectively always an insert.
    """
    url = f"https://coda.io/apis/v1/docs/{DOC}/tables/{table_id}/rows"
    payload = {
        "rows": [
            {
                "cells": [
                    {"column": col, "value": val}
                    for col, val in row_data.items()
                ]
            }
        ],
        "keyColumns": ["Thread ID link"],
    }
    for attempt in range(3):
        try:
            resp = requests.post(
                url,
                headers=CODA_HEADERS,
                json=payload,
                params={"useColumnNames": "true"},
                timeout=30,
            )
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                print(f"  ⏳ Rate limited on write, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return True
        except Exception as e:
            if attempt < 2:
                print(f"  ⚠️  Write retry {attempt + 1}: {e}")
                time.sleep(2)
            else:
                print(f"  ❌ Write failed after 3 attempts: {e}")
                return False
    return False


# ── 1. Load Settings ─────────────────────────────────────────────────
print("📋 Loading settings...")
settings_raw = coda_get(SETTINGS_TABLE)
settings = {}
for s in settings_raw:
    v = s.get("values", {})
    settings[v.get("Key", "")] = v.get("Value", "")

max_tasks = int(settings.get("email_max_tasks_per_run", str(DEFAULT_MAX_TASKS)))
task_due_setting = settings.get("email_default_task_due", "tomorrow").lower().strip()
print(f"  Max tasks per run: {max_tasks}")
print(f"  Default task due: {task_due_setting}")


# ── 2. Calculate dates ────────────────────────────────────────────────
now_et = datetime.now(TZ)
today_str = now_et.strftime("%Y-%m-%d")

if task_due_setting == "tomorrow":
    due_date = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")
elif task_due_setting == "today":
    due_date = today_str
else:
    # Try to parse as explicit date, else fall back to tomorrow
    try:
        due_date = datetime.strptime(task_due_setting, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        due_date = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")

print(f"  Today: {today_str}  Due date: {due_date}")


# ── 3. Load existing Email Tasks (dedup) ─────────────────────────────
print("🔍 Loading existing email tasks for dedup...")
existing_tasks_raw = coda_get(EMAIL_TASKS_TABLE)
existing_threads = set()
for t in existing_tasks_raw:
    v = t.get("values", {})
    thread_link = v.get("Thread ID link", "")
    if thread_link:
        existing_threads.add(thread_link.strip())
print(f"  {len(existing_threads)} existing task threads found")


# ── 4. Load Contacts ─────────────────────────────────────────────────
print("👤 Loading contacts...")
contacts_raw = coda_get(CONTACTS_TABLE)
contacts = []  # list of (name_lower, display_name)
for c in contacts_raw:
    v = c.get("values", {})
    name = v.get("Name", "").strip()
    if name:
        contacts.append((name.lower(), name))
print(f"  {len(contacts)} contacts loaded")


# ── 5. Load Projects Table (for lookup mapping) ───────────────────────
print("📁 Loading projects table...")
projects_raw = coda_get(PROJECTS_TABLE)
# Build mapping: project name (lower) → display name
project_names = {}
for p in projects_raw:
    v = p.get("values", {})
    name = v.get("Name", "").strip()
    if name:
        project_names[name.lower()] = name
print(f"  {len(project_names)} projects: {list(project_names.values())}")


# ── 6. Read Classification Input ─────────────────────────────────────
print(f"\n📥 Reading classification from {INPUT_FILE}...")
try:
    with open(INPUT_FILE, "r") as f:
        classification = json.load(f)
except FileNotFoundError:
    print(f"  ❌ Input file not found: {INPUT_FILE}")
    output = {
        "total_classified": 0,
        "tasks_needed": 0,
        "tasks_created": 0,
        "tasks_skipped": 0,
        "errors": 1,
        "error_detail": "Input file not found",
        "run_at": now_et.isoformat(),
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    exit(1)
except json.JSONDecodeError as e:
    print(f"  ❌ Failed to parse input JSON: {e}")
    output = {
        "total_classified": 0,
        "tasks_needed": 0,
        "tasks_created": 0,
        "tasks_skipped": 0,
        "errors": 1,
        "error_detail": f"JSON parse error: {e}",
        "run_at": now_et.isoformat(),
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    exit(1)

all_results = classification.get("results", [])
version = classification.get("version", "?")
total_classified = len(all_results)
print(f"  {total_classified} classified emails (v{version})")


# ── 7. Filter to task-worthy emails ──────────────────────────────────
task_candidates = [r for r in all_results if r.get("needs_task") is True]
print(f"  {len(task_candidates)} emails need tasks")

# Apply max cap
if len(task_candidates) > max_tasks:
    print(f"  ⚠️  Capping at {max_tasks} tasks (was {len(task_candidates)})")
    task_candidates = task_candidates[:max_tasks]


# ── 8. Helper: fuzzy contact match ───────────────────────────────────
def find_contact(sender: str) -> str:
    """
    Fuzzy match sender string against contacts.
    Returns the contact's display name if matched, else empty string.
    Checks if contact name appears in sender or sender appears in contact name.
    """
    sender_lower = sender.lower()
    for name_lower, display_name in contacts:
        if name_lower in sender_lower or sender_lower in name_lower:
            return display_name
        # Also try matching just words: e.g. "Chase Martin" vs "chase.martin@..."
        name_parts = name_lower.split()
        if len(name_parts) >= 2:
            first, last = name_parts[0], name_parts[-1]
            if first in sender_lower and last in sender_lower:
                return display_name
    return ""


# ── 9. Helper: map project string to Projects Table name ─────────────
def resolve_project(project_str: str) -> str:
    """
    Map the project/entity from classification to a Projects Table row name.
    Returns the matched project display name, or "Personal" as default.
    """
    if not project_str:
        return "Personal"
    p_lower = project_str.lower().strip()
    # Direct match
    if p_lower in project_names:
        return project_names[p_lower]
    # Partial match
    for key, val in project_names.items():
        if p_lower in key or key in p_lower:
            return val
    return "Personal"


# ── 10. Process each candidate ────────────────────────────────────────
print(f"\n🚀 Processing {len(task_candidates)} task candidates...")
print("=" * 70)

tasks_created = 0
tasks_skipped = 0
errors = 0
created_tasks = []

for idx, email in enumerate(task_candidates, 1):
    sender   = email.get("from", "")
    subject  = email.get("subject", "")
    account  = email.get("account", "")
    priority = email.get("priority", "Medium")
    intent   = email.get("intent", "fyi")
    reasons  = email.get("reasons", [])
    link     = email.get("link", "").strip()
    project  = email.get("project", "")

    # Truncate subject for display
    subject_display = subject[:80] if len(subject) > 80 else subject

    print(f"\n[{idx}/{len(task_candidates)}] {sender}: {subject_display}")
    print(f"  Priority={priority}  Intent={intent}  Link={'yes' if link else 'NO LINK'}")

    # ── 10a. Dedup check ─────────────────────────────────────────────
    if link and link in existing_threads:
        print(f"  ⏭️  Skipping — task already exists for this thread")
        tasks_skipped += 1
        continue

    if not link:
        print(f"  ⚠️  No thread link — creating task without dedup key")

    # ── 10b. Contact lookup ──────────────────────────────────────────
    contact_name = find_contact(sender)
    if contact_name:
        print(f"  👤 Matched contact: {contact_name}")
    else:
        print(f"  👤 No contact match for: {sender}")

    # ── 10c. Project resolution ──────────────────────────────────────
    resolved_project = resolve_project(project)
    print(f"  📁 Project: {resolved_project} (from: {project!r})")

    # ── 10d. Build task name ─────────────────────────────────────────
    task_name = subject_display  # already ≤ 80 chars

    # ── 10e. Build Notes field ───────────────────────────────────────
    # Notes consolidates Priority, Intent, Account, Reasons since there
    # are no dedicated columns for those in the actual table schema.
    reasons_str = ", ".join(reasons) if reasons else ""
    notes_parts = [
        f"Priority: {priority}",
        f"Intent: {intent}",
        f"Account: {account}",
    ]
    if reasons_str:
        notes_parts.append(f"Reasons: {reasons_str}")
    if sender:
        notes_parts.append(f"From: {sender}")
    notes_content = "\n".join(notes_parts)

    # ── 10f. Build row payload ───────────────────────────────────────
    row_data = {
        "Name": task_name,
        "Status": "Inbox",
        "Source": "Email Monitor",
        "Due date": due_date,
        "Day": today_str,
        "Email account": account,
        "Thread ID link": link,
        "Notes": notes_content,
    }

    # Only set Projects Table if we have a valid match
    if resolved_project:
        row_data["Projects Table"] = resolved_project

    # Only set Contact if we found a match
    if contact_name:
        row_data["Contact"] = contact_name

    # ── 10g. Write to Coda ───────────────────────────────────────────
    success = coda_upsert(EMAIL_TASKS_TABLE, row_data)
    if success:
        print(f"  ✅ Task created: {task_name}")
        tasks_created += 1
        # Add to dedup set so we don't double-create within the same run
        if link:
            existing_threads.add(link)
        created_tasks.append({
            "name": task_name,
            "from": sender,
            "priority": priority,
            "intent": intent,
            "project": resolved_project,
            "contact": contact_name,
        })
    else:
        print(f"  ❌ Failed to create task for: {task_name}")
        errors += 1

    # Small pause to be kind to the API
    time.sleep(0.3)


# ── 11. Summary ───────────────────────────────────────────────────────
print(f"\n{'=' * 70}")
print(f"EMAIL TASK CREATION — SUMMARY")
print(f"{'=' * 70}")
print(f"  Classified emails:   {total_classified}")
print(f"  Tasks needed:        {len(task_candidates)}")
print(f"  Tasks created:       {tasks_created} ✅")
print(f"  Tasks skipped:       {tasks_skipped} (already existed)")
print(f"  Errors:              {errors} ❌")

if created_tasks:
    print(f"\nCreated tasks:")
    for t in created_tasks:
        print(f"  • [{t['priority']}] {t['name']}")
        if t["contact"]:
            print(f"    Contact: {t['contact']}")


# ── 12. Write output JSON ─────────────────────────────────────────────
output = {
    "total_classified": total_classified,
    "tasks_needed": len(task_candidates),
    "tasks_created": tasks_created,
    "tasks_skipped": tasks_skipped,
    "errors": errors,
    "run_at": now_et.isoformat(),
    "due_date": due_date,
    "created": created_tasks,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Output saved to {OUTPUT_FILE}")
