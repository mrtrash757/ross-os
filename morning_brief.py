#!/usr/bin/env python3
"""
Ross OS — Morning Brief
Called by the Morning Brief cron at 6:30am ET.

Accepts an optional --calendar-file argument pointing to a JSON file
with today's calendar events (written by the cron agent before calling this script).

Composes a morning briefing HTML email and prints it to stdout.
Also saves a JSON summary to /home/user/workspace/morning_brief_output.json.

Data pulled from Coda:
  - Personal Tasks      (grid-G1O2W471aC)
  - Email-linked Tasks  (grid-7IWNsZiHzE)
  - Todoist Tasks       (grid-sync-48345-Task)
  - Habits              (grid-5WHcBsnbmk)
  - Habit Logs          (grid-5FJBmY91ko)
  - Settings            (grid-ybi2tIogls)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

# ── Credentials ─────────────────────────────────────────────────────────────
CODA_TOKEN = "f8b53a89-6376-486e-85d8-f59fffed59d1"
CODA_DOC   = "nSMMjxb_b2"
CODA_BASE  = f"https://coda.io/apis/v1/docs/{CODA_DOC}"
HEADERS    = {
    "Authorization": f"Bearer {CODA_TOKEN}",
    "Content-Type":  "application/json",
}

# ── Table IDs ────────────────────────────────────────────────────────────────
PERSONAL_TASKS_TABLE = "grid-G1O2W471aC"
EMAIL_TASKS_TABLE    = "grid-7IWNsZiHzE"
TODOIST_TABLE        = "grid-sync-48345-Task"
HABITS_TABLE         = "grid-5WHcBsnbmk"
HABIT_LOGS_TABLE     = "grid-5FJBmY91ko"
SETTINGS_TABLE       = "grid-ybi2tIogls"
DAYS_TABLE           = "grid-Zm8ylxf9zc"

# ── Timezone ─────────────────────────────────────────────────────────────────
def _get_et():
    try:
        from zoneinfo import ZoneInfo
        import datetime as _dt
        now = _dt.datetime.now(ZoneInfo("America/Detroit"))
        return timezone(now.utcoffset())
    except Exception:
        return timezone(timedelta(hours=-4))

ET = _get_et()

# ── Helpers ───────────────────────────────────────────────────────────────────

def now_et():
    return datetime.now(ET)


def today_str():
    return now_et().strftime("%Y-%m-%d")


def coda_get(table_id, params=None):
    """Fetch all rows from a Coda table, handling pagination and rate limits."""
    url  = f"{CODA_BASE}/tables/{table_id}/rows"
    base = {"useColumnNames": "true", "limit": 500}
    if params:
        base.update(params)
    all_rows = []
    p = base
    retries = 3
    while url:
        for attempt in range(retries):
            resp = requests.get(url, headers=HEADERS, params=p if p else None)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                print(f"   ⏳ Rate limited on {table_id}, waiting {wait}s…", file=sys.stderr)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        data = resp.json()
        all_rows.extend(data.get("items", []))
        next_link = data.get("nextPageLink")
        if next_link:
            url = next_link
            p   = {}   # nextPageLink already carries params
        else:
            url = None
    return all_rows


def coda_update_row(table_id, row_id, cells):
    """Update a specific Coda row by ID."""
    url = f"{CODA_BASE}/tables/{table_id}/rows/{row_id}"
    body = {"row": {"cells": cells}}
    for attempt in range(3):
        resp = requests.put(url, headers=HEADERS, json=body)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return True
    return False


def find_day_row_id(date_str):
    """Find the Day row ID for a given date string (YYYY-MM-DD)."""
    rows = coda_get(DAYS_TABLE)
    for r in rows:
        if date_str in str(r.get("values", {}).get("Date", "")):
            return r["id"]
    return None


def generate_intent(dow_full, personal_tasks, email_tasks, todoist_tasks, calendar_events):
    """Build a Start of day intent string from today's priorities."""
    parts = []

    # High-priority tasks across all sources
    high = [t for t in personal_tasks if t.get("priority") in ("High", "Critical")]
    med  = [t for t in personal_tasks if t.get("priority") == "Medium"]

    if high:
        parts.append("🔴 " + ", ".join(t["name"][:50] for t in high[:3]))
    if med:
        parts.append("🟡 " + ", ".join(t["name"][:50] for t in med[:3]))
    if email_tasks:
        parts.append(f"📬 {len(email_tasks)} email tasks")
    if todoist_tasks:
        parts.append(f"📝 {len(todoist_tasks)} work tasks")
    if calendar_events:
        parts.append(f"📅 {len(calendar_events)} meetings")

    if not parts:
        return f"{dow_full} — Light day. Habits + workouts."
    return f"{dow_full} focus: " + " | ".join(parts)


def read_settings(rows):
    """Build a key→value dict from the Settings table rows."""
    settings = {}
    for row in rows:
        v   = row.get("values", {})
        key = str(v.get("Key", "")).strip()
        val = str(v.get("Value", "")).strip()
        if key:
            settings[key] = val
    return settings


# ── Calendar ──────────────────────────────────────────────────────────────────

def load_calendar(path):
    """
    Load calendar events from a JSON file written by the cron agent.
    Returns a list of event dicts sorted by start time.
    The file may be a list of events directly, or {\"events\": [...]} wrapper.
    """
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path) as f:
            raw = json.load(f)
        if isinstance(raw, list):
            events = raw
        elif isinstance(raw, dict):
            # Try common wrapper keys
            events = (
                raw.get("events")
                or raw.get("items")
                or raw.get("value")
                or []
            )
        else:
            events = []

        today = today_str()
        parsed = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            summary = ev.get("summary") or ev.get("title") or ev.get("name") or "(No title)"
            # Start time — handle both dateTime and date (all-day)
            start_raw = (
                ev.get("start", {}).get("dateTime")
                or ev.get("start", {}).get("date")
                or ev.get("startTime")
                or ev.get("start")
                or ""
            )
            end_raw = (
                ev.get("end", {}).get("dateTime")
                or ev.get("end", {}).get("date")
                or ev.get("endTime")
                or ev.get("end")
                or ""
            )
            # Filter to today only
            if today not in str(start_raw):
                continue

            # Parse display time
            all_day = False
            start_dt = None
            if "T" in str(start_raw):
                try:
                    # Handle Z suffix
                    s = str(start_raw).replace("Z", "+00:00")
                    start_dt = datetime.fromisoformat(s).astimezone(ET)
                except Exception:
                    pass
            else:
                all_day = True

            parsed.append({
                "summary":  summary,
                "start_raw": start_raw,
                "end_raw":   end_raw,
                "start_dt":  start_dt,
                "all_day":   all_day,
                "location":  ev.get("location", ""),
                "description": ev.get("description", ""),
            })

        # Sort: all-day first, then by start_dt
        parsed.sort(key=lambda e: (
            0 if e["all_day"] else 1,
            e["start_dt"] or datetime.min.replace(tzinfo=ET)
        ))
        return parsed
    except Exception as ex:
        print(f"   ⚠️  Calendar parse error: {ex}", file=sys.stderr)
        return []


def fmt_event_time(ev):
    if ev["all_day"]:
        return "All day"
    if ev["start_dt"]:
        s = ev["start_dt"].strftime("%-I:%M %p")
        # Parse end too
        end_raw = ev.get("end_raw", "")
        if "T" in str(end_raw):
            try:
                e_str = str(end_raw).replace("Z", "+00:00")
                end_dt = datetime.fromisoformat(e_str).astimezone(ET)
                s += f" – {end_dt.strftime('%-I:%M %p')}"
            except Exception:
                pass
        return s
    return ""


# ── Task fetchers ─────────────────────────────────────────────────────────────

DONE_STATUSES = {"done", "completed", "complete", "closed", "cancelled", "canceled"}


def fetch_personal_tasks():
    """Fetch active Personal Tasks (Status not Done/Completed)."""
    print("   Fetching Personal Tasks…", file=sys.stderr)
    rows = coda_get(PERSONAL_TASKS_TABLE)
    tasks = []
    for row in rows:
        v      = row.get("values", {})
        status = str(v.get("Status", "")).strip().lower()
        if status in DONE_STATUSES:
            continue
        name     = str(v.get("Name", "")).strip()
        priority = str(v.get("Priority", "")).strip()
        due      = str(v.get("Due date", "") or v.get("Due Date", "") or v.get("Due", "")).strip()
        project  = str(v.get("Project", "")).strip()
        if not name:
            continue
        tasks.append({
            "source":   "Personal",
            "name":     name,
            "priority": priority or "None",
            "due":      due,
            "project":  project,
            "status":   str(v.get("Status", "")).strip(),
        })
    return tasks


def fetch_email_tasks():
    """Fetch active Email-linked Tasks."""
    print("   Fetching Email Tasks…", file=sys.stderr)
    rows = coda_get(EMAIL_TASKS_TABLE)
    tasks = []
    for row in rows:
        v      = row.get("values", {})
        status = str(v.get("Status", "")).strip().lower()
        if status in DONE_STATUSES:
            continue
        name     = str(v.get("Name", "") or v.get("Task", "")).strip()
        priority = str(v.get("Priority", "")).strip()
        due      = str(v.get("Due date", "") or v.get("Due Date", "") or v.get("Due", "")).strip()
        if not name:
            continue
        tasks.append({
            "source":   "Email",
            "name":     name,
            "priority": priority or "None",
            "due":      due,
            "status":   str(v.get("Status", "")).strip(),
        })
    return tasks


def fetch_todoist_tasks():
    """Fetch active Todoist Tasks (Checked = false)."""
    print("   Fetching Todoist Tasks…", file=sys.stderr)
    rows = coda_get(TODOIST_TABLE)
    tasks = []
    for row in rows:
        v       = row.get("values", {})
        checked = v.get("Checked")
        # Coda sync booleans can be True/False or "true"/"false"
        if isinstance(checked, bool) and checked:
            continue
        if isinstance(checked, str) and checked.lower() == "true":
            continue
        content = str(v.get("Content", "")).strip()
        if not content:
            continue
        due     = str(v.get("Due date", "") or "").strip()
        project = str(v.get("Project", "") or "").strip()
        labels  = str(v.get("Labels", "") or "").strip()
        tasks.append({
            "source":   "Todoist",
            "name":     content,
            "priority": "None",
            "due":      due,
            "project":  project,
            "labels":   labels,
        })
    return tasks


# ── Habits ────────────────────────────────────────────────────────────────────

def fetch_habit_summary():
    """
    Return yesterday's habit completion status.
    Returns list of {habit, completed} dicts.
    """
    print("   Fetching Habits and Habit Logs…", file=sys.stderr)
    yesterday = (now_et() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Active habits
    habit_rows   = coda_get(HABITS_TABLE)
    active_names = [
        r["values"]["Name"].strip()
        for r in habit_rows
        if r.get("values", {}).get("Active?") is True
        and r.get("values", {}).get("Name", "").strip()
    ]

    # Yesterday's logs
    log_rows = coda_get(HABIT_LOGS_TABLE)
    completion = {}
    for row in log_rows:
        v        = row.get("values", {})
        log_date = str(v.get("Date", "")).strip()
        if yesterday not in log_date:
            continue
        habit_name = str(v.get("Habit", "")).strip()
        completed  = v.get("Completed?")
        if isinstance(completed, str):
            completed = completed.lower() == "true"
        completion[habit_name] = bool(completed)

    results = []
    for name in active_names:
        results.append({
            "habit":     name,
            "completed": completion.get(name, None),  # None = no log found
        })
    return results, yesterday


# ── Priority sorting ──────────────────────────────────────────────────────────

PRIORITY_ORDER = {"high": 0, "medium": 1, "med": 1, "low": 2, "none": 3, "": 4}


def priority_key(task):
    return PRIORITY_ORDER.get(task.get("priority", "").lower(), 4)


def group_tasks_by_priority(tasks):
    """Return {High: [...], Medium: [...], Low: [...], None: [...]}"""
    groups = {"High": [], "Medium": [], "Low": [], "None": []}
    for t in tasks:
        p = t.get("priority", "").strip()
        if p.lower() == "high":
            groups["High"].append(t)
        elif p.lower() in ("medium", "med"):
            groups["Medium"].append(t)
        elif p.lower() == "low":
            groups["Low"].append(t)
        else:
            groups["None"].append(t)
    return groups


# ── HTML builder ──────────────────────────────────────────────────────────────

# Inline CSS palette
C_BG       = "#f9f9f9"
C_WHITE    = "#ffffff"
C_BORDER   = "#e5e7eb"
C_TEXT     = "#1a1a1a"
C_MUTED    = "#6b7280"
C_HIGH     = "#dc2626"   # red
C_MEDIUM   = "#d97706"   # amber
C_LOW      = "#16a34a"   # green
C_ACCENT   = "#2563eb"   # blue
C_HABIT_OK = "#16a34a"
C_HABIT_NO = "#dc2626"
C_HABIT_UN = "#9ca3af"

FONT = "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;"


def _section(title, content_html, icon=""):
    """Wrap content in a named card section."""
    return f"""
<div style="background:{C_WHITE}; border:1px solid {C_BORDER}; border-radius:8px;
            margin:0 0 20px 0; overflow:hidden;">
  <div style="background:#f3f4f6; padding:12px 20px; border-bottom:1px solid {C_BORDER};">
    <h2 style="margin:0; {FONT} font-size:15px; font-weight:600; color:{C_TEXT};
               letter-spacing:0.02em;">{icon} {title}</h2>
  </div>
  <div style="padding:16px 20px;">
    {content_html}
  </div>
</div>"""


def _empty(msg="Nothing to show."):
    return f'<p style="margin:0; {FONT} font-size:14px; color:{C_MUTED};">{msg}</p>'


def build_calendar_html(events):
    if not events:
        return _empty("No events today.")
    rows = []
    for ev in events:
        time_str = fmt_event_time(ev)
        loc = f' <span style="color:{C_MUTED}; font-size:12px;">📍 {ev["location"]}</span>' if ev.get("location") else ""
        rows.append(
            f'<div style="display:flex; align-items:baseline; gap:12px; '
            f'padding:8px 0; border-bottom:1px solid {C_BORDER};">'
            f'  <span style="{FONT} font-size:12px; color:{C_MUTED}; '
            f'         min-width:110px; flex-shrink:0;">{time_str}</span>'
            f'  <span style="{FONT} font-size:14px; color:{C_TEXT}; font-weight:500;">'
            f'{ev["summary"]}{loc}</span>'
            f'</div>'
        )
    return "\n".join(rows)


def _priority_badge(priority):
    color = {
        "high":   C_HIGH,
        "medium": C_MEDIUM,
        "med":    C_MEDIUM,
        "low":    C_LOW,
    }.get(priority.lower(), C_MUTED)
    label = priority if priority else "—"
    return (
        f'<span style="background:{color}; color:#fff; font-size:11px; '
        f'font-weight:600; padding:2px 7px; border-radius:10px; '
        f'{FONT} margin-left:8px;">{label}</span>'
    )


def _task_row(task, show_source=False):
    name     = task["name"]
    priority = task.get("priority", "")
    due      = task.get("due", "")
    source   = task.get("source", "")
    # Clean up ISO dates to just YYYY-MM-DD
    if due and "T" in due:
        due = due[:10]
    meta_parts = []
    if show_source and source:
        meta_parts.append(f'<span style="color:{C_ACCENT};">{source}</span>')
    if due:
        meta_parts.append(f'Due {due}')
    if task.get("project"):
        meta_parts.append(task["project"])
    if task.get("labels"):
        meta_parts.append(task["labels"])
    meta_html = (
        f' <span style="{FONT} font-size:12px; color:{C_MUTED};">'
        + " · ".join(meta_parts) + "</span>"
    ) if meta_parts else ""
    badge = _priority_badge(priority) if priority and priority.lower() != "none" else ""
    return (
        f'<div style="padding:7px 0; border-bottom:1px solid {C_BORDER}; '
        f'display:flex; align-items:baseline; gap:6px;">'
        f'  <span style="{FONT} font-size:14px; color:{C_TEXT};">• {name}</span>'
        f'  {badge}{meta_html}'
        f'</div>'
    )


def build_tasks_html(personal, email, todoist):
    all_tasks = personal + email + todoist
    if not all_tasks:
        return _empty("No active tasks.")
    groups = group_tasks_by_priority(all_tasks)
    html   = []
    for level in ("High", "Medium", "Low", "None"):
        tasks = groups[level]
        if not tasks:
            continue
        color = {"High": C_HIGH, "Medium": C_MEDIUM,
                 "Low": C_LOW, "None": C_MUTED}[level]
        html.append(
            f'<div style="margin-bottom:12px;">'
            f'  <div style="{FONT} font-size:12px; font-weight:700; '
            f'             color:{color}; text-transform:uppercase; '
            f'             letter-spacing:0.08em; margin-bottom:4px;">'
            f'    {level} Priority</div>'
        )
        for t in tasks:
            html.append(_task_row(t, show_source=True))
        html.append("</div>")
    # Summary line
    total = len(all_tasks)
    p_cnt = len(personal)
    e_cnt = len(email)
    td_cnt = len(todoist)
    html.append(
        f'<p style="{FONT} font-size:12px; color:{C_MUTED}; margin:12px 0 0 0;">'
        f'{total} active tasks — {p_cnt} personal · {e_cnt} email · {td_cnt} Todoist</p>'
    )
    return "\n".join(html)


def build_habits_html(habit_summary, yesterday):
    if not habit_summary:
        return _empty("No active habits configured.")
    rows  = []
    total = len(habit_summary)
    done  = sum(1 for h in habit_summary if h["completed"] is True)
    rows.append(
        f'<p style="{FONT} font-size:13px; color:{C_MUTED}; margin:0 0 10px 0;">'
        f'Yesterday ({yesterday}) — {done}/{total} kept</p>'
    )
    for h in habit_summary:
        completed = h["completed"]
        if completed is True:
            icon  = "✅"
            color = C_HABIT_OK
            label = "Kept"
        elif completed is False:
            icon  = "❌"
            color = C_HABIT_NO
            label = "Missed"
        else:
            icon  = "—"
            color = C_HABIT_UN
            label = "No log"
        rows.append(
            f'<div style="display:flex; align-items:center; gap:10px; '
            f'            padding:7px 0; border-bottom:1px solid {C_BORDER};">'
            f'  <span style="font-size:16px;">{icon}</span>'
            f'  <span style="{FONT} font-size:14px; color:{C_TEXT}; '
            f'               flex:1;">{h["habit"]}</span>'
            f'  <span style="{FONT} font-size:12px; color:{color}; '
            f'               font-weight:600;">{label}</span>'
            f'</div>'
        )
    return "\n".join(rows)


def build_sleep_energy_prompt_html():
    """Build a Sleep/Energy reply prompt section for the morning brief email."""
    return f"""
<p style="margin:0 0 12px 0; {FONT} font-size:14px; color:{C_TEXT};">
  Reply to this email with your sleep and energy to log it automatically:
</p>
<div style="background:#f3f4f6; border-radius:6px; padding:12px 16px; margin:0 0 8px 0;
            border-left:3px solid #2563eb;">
  <code style="{FONT} font-size:14px; color:#1e3a5f;">Sleep: 7h &nbsp;&nbsp; Energy: High</code>
</div>
<p style="margin:0; {FONT} font-size:12px; color:{C_MUTED};">
  Energy options: Low, Medium, High &nbsp;|&nbsp; Sleep: any format (7h, 7.5 hours, etc.)
</p>
"""


def build_intent_html(intent_text):
    """Build a Today's Focus section showing the auto-generated intent."""
    return f"""
<div style="background:linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius:6px; padding:14px 18px; border-left:3px solid #2563eb;">
  <p style="margin:0; {FONT} font-size:15px; font-weight:600; color:#1e3a5f;">
    {intent_text}
  </p>
</div>
"""


def build_html(
    date_str,
    dow_full,
    calendar_events,
    personal_tasks,
    email_tasks,
    todoist_tasks,
    habit_summary,
    yesterday,
    generated_at,
    intent_text="",
):
    cal_html     = build_calendar_html(calendar_events)
    tasks_html   = build_tasks_html(personal_tasks, email_tasks, todoist_tasks)
    habits_html  = build_habits_html(habit_summary, yesterday)
    intent_html  = build_intent_html(intent_text) if intent_text else _empty("No priorities set.")
    sleep_html   = build_sleep_energy_prompt_html()

    # Header greeting
    dow_display  = f"{dow_full}, {date_str}"
    total_events = len(calendar_events)
    total_tasks  = len(personal_tasks) + len(email_tasks) + len(todoist_tasks)
    habits_done  = sum(1 for h in habit_summary if h["completed"] is True)
    habits_total = len(habit_summary)

    header_html = f"""
<div style="background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
            padding: 32px 32px 24px; border-radius:8px 8px 0 0; margin-bottom:0;">
  <h1 style="{FONT} font-size:26px; font-weight:700; color:#ffffff; margin:0 0 6px 0;">
    Good morning, Ross ☀️
  </h1>
  <p style="{FONT} font-size:15px; color:rgba(255,255,255,0.8); margin:0 0 16px 0;">
    {dow_display}
  </p>
  <div style="display:flex; gap:16px; flex-wrap:wrap;">
    <div style="background:rgba(255,255,255,0.15); border-radius:6px; padding:8px 14px;">
      <span style="{FONT} font-size:12px; color:rgba(255,255,255,0.7);">Events</span><br>
      <span style="{FONT} font-size:18px; font-weight:700; color:#fff;">{total_events}</span>
    </div>
    <div style="background:rgba(255,255,255,0.15); border-radius:6px; padding:8px 14px;">
      <span style="{FONT} font-size:12px; color:rgba(255,255,255,0.7);">Open Tasks</span><br>
      <span style="{FONT} font-size:18px; font-weight:700; color:#fff;">{total_tasks}</span>
    </div>
    <div style="background:rgba(255,255,255,0.15); border-radius:6px; padding:8px 14px;">
      <span style="{FONT} font-size:12px; color:rgba(255,255,255,0.7);">Habits (Yesterday)</span><br>
      <span style="{FONT} font-size:18px; font-weight:700; color:#fff;">{habits_done}/{habits_total}</span>
    </div>
  </div>
</div>"""

    footer_html = f"""
<div style="text-align:center; padding:20px; margin-top:8px;">
  <p style="{FONT} font-size:12px; color:{C_MUTED}; margin:0;">
    Generated by Ross OS at {generated_at} ET
  </p>
</div>"""

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Brief — {date_str}</title>
</head>
<body style="margin:0; padding:0; background:{C_BG};">
  <div style="max-width:680px; margin:0 auto; padding:20px 16px; {FONT}">
    {header_html}
    <div style="height:20px;"></div>
    {_section("Today's Focus", intent_html, "🎯")}
    {_section("Today's Schedule", cal_html, "📅")}
    {_section("Open Tasks", tasks_html, "✅")}
    {_section("Habits — Yesterday", habits_html, "🔥")}
    {_section("Log Sleep & Energy", sleep_html, "💤")}
    {footer_html}
  </div>
</body>
</html>"""
    return body


# ── JSON summary ──────────────────────────────────────────────────────────────

def build_json_summary(
    date_str,
    calendar_events,
    personal_tasks,
    email_tasks,
    todoist_tasks,
    habit_summary,
):
    # Task breakdown by source + priority
    def breakdown(tasks, source):
        g = group_tasks_by_priority(tasks)
        return {
            "source": source,
            "total":  len(tasks),
            "high":   len(g["High"]),
            "medium": len(g["Medium"]),
            "low":    len(g["Low"]),
            "none":   len(g["None"]),
        }

    habits_done  = sum(1 for h in habit_summary if h["completed"] is True)
    habits_total = len(habit_summary)

    return {
        "date":            date_str,
        "calendar_events": len(calendar_events),
        "tasks": {
            "total":    len(personal_tasks) + len(email_tasks) + len(todoist_tasks),
            "personal": breakdown(personal_tasks, "Personal"),
            "email":    breakdown(email_tasks,    "Email"),
            "todoist":  breakdown(todoist_tasks,  "Todoist"),
        },
        "habits_yesterday": {
            "completed": habits_done,
            "total":     habits_total,
        },
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def run(calendar_file=None):
    now        = now_et()
    date_str   = now.strftime("%Y-%m-%d")
    dow_full   = now.strftime("%A")
    generated  = now.strftime("%Y-%m-%d %I:%M %p")

    print(f"🌅 Morning Brief — {dow_full}, {date_str}", file=sys.stderr)

    # ── 1. Settings ─────────────────────────────────────────────────
    print("\n1️⃣  Loading settings…", file=sys.stderr)
    try:
        settings_rows = coda_get(SETTINGS_TABLE)
        settings      = read_settings(settings_rows)
    except Exception as e:
        print(f"   ⚠️  Settings error: {e} — using defaults", file=sys.stderr)

    # ── 2. Calendar ─────────────────────────────────────────────────
    print("\n2️⃣  Loading calendar…", file=sys.stderr)
    calendar_events = load_calendar(calendar_file)
    print(f"   {len(calendar_events)} events today", file=sys.stderr)

    # ── 3. Tasks ─────────────────────────────────────────────────────
    print("\n3️⃣  Fetching tasks…", file=sys.stderr)
    try:
        personal_tasks = fetch_personal_tasks()
    except Exception as e:
        print(f"   ❌ Personal tasks error: {e}", file=sys.stderr)
        personal_tasks = []

    try:
        email_tasks = fetch_email_tasks()
    except Exception as e:
        print(f"   ❌ Email tasks error: {e}", file=sys.stderr)
        email_tasks = []

    try:
        todoist_tasks = fetch_todoist_tasks()
    except Exception as e:
        print(f"   ❌ Todoist tasks error: {e}", file=sys.stderr)
        todoist_tasks = []

    print(
        f"   {len(personal_tasks)} personal · {len(email_tasks)} email · {len(todoist_tasks)} Todoist",
        file=sys.stderr
    )

    # ── 4. Habits ─────────────────────────────────────────────────────
    print("\n5️⃣  Loading habits…", file=sys.stderr)
    try:
        habit_summary, yesterday = fetch_habit_summary()
    except Exception as e:
        print(f"   ❌ Habits error: {e}", file=sys.stderr)
        habit_summary = []
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    done_count  = sum(1 for h in habit_summary if h["completed"] is True)
    total_count = len(habit_summary)
    print(f"   {done_count}/{total_count} habits kept yesterday ({yesterday})", file=sys.stderr)

    # ── 6. Generate intent + write to Day row ───────────────────────
    print("\n6️⃣  Generating intent + writing to Day row…", file=sys.stderr)
    intent_text = ""
    try:
        intent_text = generate_intent(
            dow_full, personal_tasks, email_tasks, todoist_tasks, calendar_events
        )
        print(f"   Intent: {intent_text}", file=sys.stderr)

        day_row_id = find_day_row_id(date_str)
        if day_row_id:
            coda_update_row(DAYS_TABLE, day_row_id, [
                {"column": "Start of day intent", "value": intent_text},
            ])
            print(f"   ✅ Intent written to Day row {day_row_id}", file=sys.stderr)
        else:
            print(f"   ⚠️  No Day row found for {date_str} — intent not saved", file=sys.stderr)
    except Exception as e:
        print(f"   ❌ Intent error: {e}", file=sys.stderr)

    # ── 7. Build HTML ─────────────────────────────────────────────────
    print("\n7️⃣  Building email…", file=sys.stderr)
    html = build_html(
        date_str        = date_str,
        dow_full        = dow_full,
        calendar_events = calendar_events,
        personal_tasks  = personal_tasks,
        email_tasks     = email_tasks,
        todoist_tasks   = todoist_tasks,
        habit_summary   = habit_summary,
        yesterday       = yesterday,
        generated_at    = generated,
        intent_text     = intent_text,
    )

    # ── 8. Print HTML to stdout ───────────────────────────────────────
    print(html)

    # ── 9. Save JSON summary ──────────────────────────────────────────
    out_path = "/home/user/workspace/morning_brief_output.json"
    summary  = build_json_summary(
        date_str        = date_str,
        calendar_events = calendar_events,
        personal_tasks  = personal_tasks,
        email_tasks     = email_tasks,
        todoist_tasks   = todoist_tasks,
        habit_summary   = habit_summary,
    )
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n💾 JSON summary saved to {out_path}", file=sys.stderr)
    print(f"📊 {summary['tasks']['total']} tasks · {summary['calendar_events']} events · "
          f"{summary['habits_yesterday']['completed']}/{summary['habits_yesterday']['total']} habits",
          file=sys.stderr)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ross OS Morning Brief")
    parser.add_argument(
        "--calendar-file",
        default=None,
        help="Path to JSON file with today's calendar events",
    )
    args = parser.parse_args()
    run(calendar_file=args.calendar_file)
