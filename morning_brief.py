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
  - Contacts            (grid-1M2UOaliIC)
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
CONTACTS_TABLE       = "grid-1M2UOaliIC"
HABITS_TABLE         = "grid-5WHcBsnbmk"
HABIT_LOGS_TABLE     = "grid-5FJBmY91ko"
SETTINGS_TABLE       = "grid-ybi2tIogls"

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
    The file may be a list of events directly, or {"events": [...]} wrapper.
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
        contact  = str(v.get("Contact", "")).strip()
        if not name:
            continue
        tasks.append({
            "source":   "Email",
            "name":     name,
            "priority": priority or "None",
            "due":      due,
            "contact":  contact,
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


# ── Contacts ──────────────────────────────────────────────────────────────────

def fetch_stale_contacts(stale_days=7):
    """
    Return contacts with Last interaction > stale_days ago.
    Only include Importance = High or Medium.
    """
    print("   Fetching Contacts…", file=sys.stderr)
    rows  = coda_get(CONTACTS_TABLE)
    today = now_et().replace(hour=0, minute=0, second=0, microsecond=0)
    stale = []
    for row in rows:
        v          = row.get("values", {})
        importance = str(v.get("Importance", "")).strip()
        if importance not in ("High", "Med", "Medium"):
            continue
        name = str(v.get("Name", "") or v.get("Full Name", "")).strip()
        if not name:
            continue
        last_raw = str(v.get("Last interaction date", "") or v.get("Last interaction", "") or v.get("Last Interaction", "")).strip()
        if not last_raw:
            continue
        # Parse the date
        last_dt = None
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                if "T" in last_raw:
                    last_dt = datetime.fromisoformat(
                        last_raw.replace("Z", "+00:00")
                    ).astimezone(ET).replace(tzinfo=None)
                else:
                    last_dt = datetime.strptime(last_raw[:10], "%Y-%m-%d")
                break
            except Exception:
                continue
        if last_dt is None:
            continue
        today_naive = today.replace(tzinfo=None)
        days_since  = (today_naive - last_dt).days
        if days_since < stale_days:
            continue
        org = str(v.get("Company", "") or v.get("Organization", "") or v.get("Org", "")).strip()
        stale.append({
            "name":        name,
            "org":         org,
            "importance":  importance,
            "days_since":  days_since,
            "last_date":   last_raw[:10] if len(last_raw) >= 10 else last_raw,
        })
    # Sort by days since (most stale first)
    stale.sort(key=lambda c: c["days_since"], reverse=True)
    return stale


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
    if task.get("contact"):
        meta_parts.append(task["contact"])
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


def build_stale_contacts_html(stale_contacts):
    if not stale_contacts:
        return _empty("No stale contacts. Network is fresh. ✅")
    rows = []
    for c in stale_contacts:
        importance_color = C_HIGH if c["importance"] == "High" else C_MEDIUM
        org_part = f' <span style="color:{C_MUTED}; font-size:12px;">@ {c["org"]}</span>' if c["org"] else ""
        rows.append(
            f'<div style="display:flex; align-items:baseline; justify-content:space-between; '
            f'            padding:7px 0; border-bottom:1px solid {C_BORDER};">'
            f'  <span style="{FONT} font-size:14px; color:{C_TEXT}; font-weight:500;">'
            f'{c["name"]}{org_part}</span>'
            f'  <span style="white-space:nowrap;">'
            f'    <span style="background:{importance_color}; color:#fff; font-size:11px; '
            f'           font-weight:600; padding:2px 6px; border-radius:10px; '
            f'           {FONT} margin-right:8px;">{c["importance"]}</span>'
            f'    <span style="{FONT} font-size:13px; color:{C_MUTED};">'
            f'      {c["days_since"]}d ago</span>'
            f'  </span>'
            f'</div>'
        )
    count = len(stale_contacts)
    high  = sum(1 for c in stale_contacts if c["importance"] == "High")
    rows.append(
        f'<p style="{FONT} font-size:12px; color:{C_MUTED}; margin:12px 0 0 0;">'
        f'{count} stale contacts — {high} high importance</p>'
    )
    return "\n".join(rows)


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


def build_html(
    date_str,
    dow_full,
    calendar_events,
    personal_tasks,
    email_tasks,
    todoist_tasks,
    stale_contacts,
    habit_summary,
    yesterday,
    generated_at,
):
    cal_html     = build_calendar_html(calendar_events)
    tasks_html   = build_tasks_html(personal_tasks, email_tasks, todoist_tasks)
    stale_html   = build_stale_contacts_html(stale_contacts)
    habits_html  = build_habits_html(habit_summary, yesterday)

    # Header greeting
    dow_display  = f"{dow_full}, {date_str}"
    total_events = len(calendar_events)
    total_tasks  = len(personal_tasks) + len(email_tasks) + len(todoist_tasks)
    total_stale  = len(stale_contacts)
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
      <span style="{FONT} font-size:12px; color:rgba(255,255,255,0.7);">Stale Contacts</span><br>
      <span style="{FONT} font-size:18px; font-weight:700; color:#fff;">{total_stale}</span>
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
    {_section("Today's Schedule", cal_html, "📅")}
    {_section("Open Tasks", tasks_html, "✅")}
    {_section("Stale Contacts", stale_html, "👥")}
    {_section("Habits — Yesterday", habits_html, "🔥")}
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
    stale_contacts,
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
        "stale_contacts":   len(stale_contacts),
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
        stale_days    = int(settings.get("stale_contact_red_days", "7"))
        print(f"   stale_contact_red_days = {stale_days}", file=sys.stderr)
    except Exception as e:
        print(f"   ⚠️  Settings error: {e} — using defaults", file=sys.stderr)
        stale_days = 7

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

    # ── 4. Contacts ───────────────────────────────────────────────────
    print("\n4️⃣  Checking stale contacts…", file=sys.stderr)
    try:
        stale_contacts = fetch_stale_contacts(stale_days)
    except Exception as e:
        print(f"   ❌ Contacts error: {e}", file=sys.stderr)
        stale_contacts = []
    print(f"   {len(stale_contacts)} stale (>{stale_days}d)", file=sys.stderr)

    # ── 5. Habits ─────────────────────────────────────────────────────
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

    # ── 6. Build HTML ─────────────────────────────────────────────────
    print("\n6️⃣  Building email…", file=sys.stderr)
    html = build_html(
        date_str        = date_str,
        dow_full        = dow_full,
        calendar_events = calendar_events,
        personal_tasks  = personal_tasks,
        email_tasks     = email_tasks,
        todoist_tasks   = todoist_tasks,
        stale_contacts  = stale_contacts,
        habit_summary   = habit_summary,
        yesterday       = yesterday,
        generated_at    = generated,
    )

    # ── 7. Print HTML to stdout ───────────────────────────────────────
    print(html)

    # ── 8. Save JSON summary ──────────────────────────────────────────
    out_path = "/home/user/workspace/morning_brief_output.json"
    summary  = build_json_summary(
        date_str        = date_str,
        calendar_events = calendar_events,
        personal_tasks  = personal_tasks,
        email_tasks     = email_tasks,
        todoist_tasks   = todoist_tasks,
        stale_contacts  = stale_contacts,
        habit_summary   = habit_summary,
    )
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n💾 JSON summary saved to {out_path}", file=sys.stderr)
    print(f"📊 {summary['tasks']['total']} tasks · {summary['calendar_events']} events · "
          f"{summary['stale_contacts']} stale contacts · "
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
