#!/usr/bin/env python3
"""
Ross OS — Email Classifier v3
Reads rules from Coda Email Filter Rules table instead of Settings CSVs.
Called by the email monitor cron (hourly).

Rule evaluation order (first match wins within each tier):
  1. Sender rules
  2. Domain rules  
  3. Superhuman label rules
  4. Label rules
  5. Subject keyword rules
  6. Body keyword rules

If no rule matches, falls back to:
  - VIP contact check (High importance contacts → High priority)
  - Known contact check → Medium
  - Default → Medium / fyi
"""

import json, re, time
import requests
from datetime import datetime
from collections import Counter

TOKEN = "f8b53a89-6376-486e-85d8-f59fffed59d1"
DOC = "nSMMjxb_b2"

# Table IDs
SETTINGS_TABLE = "grid-ybi2tIogls"
EMAIL_RULES_TABLE = "grid-X_l2ntl-AQ"
CONTACTS_TABLE = "grid-1M2UOaliIC"
EMAIL_TASKS_TABLE = "grid-7IWNsZiHzE"
EMAILS_TABLE = "grid-sync-1004-Email"

CODA_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

def coda_get(table_id, limit=500):
    """Fetch rows from Coda table with pagination and retries."""
    all_rows = []
    url = f"https://coda.io/apis/v1/docs/{DOC}/tables/{table_id}/rows"
    params = {"useColumnNames": "true", "limit": str(limit)}
    while url:
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=CODA_HEADERS, params=params, timeout=20)
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 5))
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < 2:
                    print(f"  Retry {attempt+1} for {table_id}: {e}")
                    time.sleep(2)
                else:
                    print(f"  ERROR: Failed to fetch {table_id} after 3 attempts: {e}")
                    return all_rows
        all_rows.extend(data.get("items", []))
        next_uri = data.get("nextPageLink")
        if next_uri:
            url = next_uri
            params = {}  # pagination URL includes params
        else:
            url = None
    return all_rows


# ── 1. Load Settings (only global ones now) ─────────────────────────
print("Loading settings...")
settings_raw = coda_get(SETTINGS_TABLE)
settings = {}
for s in settings_raw:
    v = s.get("values", {})
    settings[v.get("Key", "")] = v.get("Value", "")

ENABLED = settings.get("email_monitor_enabled", "true").lower() == "true"
MAX_TASKS = int(settings.get("email_max_tasks_per_run", "10"))
PROJECT_MAPPING = {}
for pair in settings.get("email_project_mapping", "").split(","):
    if ":" in pair:
        email, project = pair.strip().split(":", 1)
        PROJECT_MAPPING[email.strip().lower()] = project.strip()

if not ENABLED:
    print("Email monitor disabled. Exiting.")
    with open("/home/user/workspace/email_classification_v3.json", "w") as f:
        json.dump({"total": 0, "results": [], "disabled": True}, f)
    exit(0)

print(f"  Max tasks per run: {MAX_TASKS}")
print(f"  Project mapping: {PROJECT_MAPPING}")


# ── 2. Load Email Filter Rules ──────────────────────────────────────
print("Loading email filter rules...")
rules_raw = coda_get(EMAIL_RULES_TABLE)

# Parse and organize rules by match type
rules_by_type = {
    "Sender": [],
    "Domain": [],
    "Subject keyword": [],
    "Body keyword": [],
    "Superhuman label": [],
    "Label": [],
}

for r in rules_raw:
    v = r.get("values", {})
    if not v.get("Active", False):
        continue
    
    match_type = v.get("Match Type", "")
    pattern = str(v.get("Pattern", "")).strip().lower()
    if not match_type or not pattern:
        continue
    
    rule = {
        "name": v.get("Name", ""),
        "match_type": match_type,
        "pattern": pattern,
        "priority": v.get("Priority", "Medium"),
        "action": v.get("Action Required", "fyi"),
        "needs_task": v.get("Needs Task", False),
        "entity": v.get("Entity", ""),
    }
    
    if match_type in rules_by_type:
        rules_by_type[match_type].append(rule)

total_rules = sum(len(v) for v in rules_by_type.values())
print(f"  Loaded {total_rules} active rules:")
for mt, rl in rules_by_type.items():
    if rl:
        print(f"    {mt}: {len(rl)}")


# ── 3. Load Contacts ────────────────────────────────────────────────
print("Loading contacts...")
contacts_raw = coda_get(CONTACTS_TABLE)
contacts = {}
for c in contacts_raw:
    v = c.get("values", {})
    name = v.get("Name", "").strip()
    if name:
        contacts[name.lower()] = {
            "name": name,
            "org": v.get("Org", ""),
            "importance": v.get("Importance", ""),
        }
print(f"  {len(contacts)} contacts")


# ── 4. Load Existing Tasks (dedup) ──────────────────────────────────
print("Loading existing email tasks...")
existing_tasks = coda_get(EMAIL_TASKS_TABLE)
existing_threads = set()
for t in existing_tasks:
    v = t.get("values", {})
    link = v.get("Thread ID link", "")
    if link:
        existing_threads.add(link)
print(f"  {len(existing_threads)} existing task threads")


# ── 5. Load Emails ──────────────────────────────────────────────────
print("Loading emails...")
emails = coda_get(EMAILS_TABLE)
print(f"  {len(emails)} emails")


# ── 6. Classify ─────────────────────────────────────────────────────
def match_rules(sender_lower, domain, labels_str, subject_lower, body_lower):
    """
    Try to match email against rules. Returns first matching rule or None.
    Evaluation order: Sender > Domain > Superhuman label > Label > Subject keyword > Body keyword
    """
    # Sender rules
    for rule in rules_by_type["Sender"]:
        if rule["pattern"] in sender_lower:
            return rule
    
    # Domain rules
    for rule in rules_by_type["Domain"]:
        if rule["pattern"] in domain:
            return rule
    
    # Superhuman label rules
    sh_labels = []
    if "[Superhuman]/AI/Respond" in labels_str:
        sh_labels.append("respond")
    if "[Superhuman]/AI/Waiting" in labels_str:
        sh_labels.append("waiting")
    if "[Superhuman]/AI/Meeting" in labels_str:
        sh_labels.append("meeting")
    if "[Superhuman]/AI/Marketing" in labels_str:
        sh_labels.append("marketing")
    if "[Superhuman]/AI/News" in labels_str:
        sh_labels.append("news")
    if "[Superhuman]/ru" in labels_str:
        sh_labels.append("ru")
    
    for rule in rules_by_type["Superhuman label"]:
        if rule["pattern"] in sh_labels:
            return rule
    
    # Label rules
    for rule in rules_by_type["Label"]:
        if rule["pattern"] in labels_str:
            return rule
    
    # Subject keyword rules
    for rule in rules_by_type["Subject keyword"]:
        if rule["pattern"] in subject_lower:
            return rule
    
    # Body keyword rules
    text_lower = subject_lower + " " + body_lower
    for rule in rules_by_type["Body keyword"]:
        if rule["pattern"] in text_lower:
            return rule
    
    return None


def check_contacts(sender_lower):
    """Check if sender matches a known contact. Returns (priority, reason) or None."""
    for cname, cdata in contacts.items():
        if cname in sender_lower or sender_lower in cname:
            if cdata["importance"] == "High":
                return "High", f"VIP contact: {cdata['name']}"
            else:
                return "Medium", f"Known contact: {cdata['name']}"
    return None, None


# Ross's own email addresses — skip emails sent by Ross himself
OWN_EMAILS = {v.lower() for v in PROJECT_MAPPING.keys()}

# ── 6a. Pre-filter: INBOX only, skip self-sent ─────────────────────
inbox_emails = []
for email in emails:
    v = email.get("values", {})
    labels = str(v.get("Labels", ""))
    sender = str(v.get("From", ""))
    
    if "INBOX" not in labels:
        continue
    
    # Skip emails sent by Ross (own replies showing up in inbox)
    sender_lower = sender.lower()
    if any(own in sender_lower for own in OWN_EMAILS):
        continue
    
    inbox_emails.append(email)

print(f"  After filtering: {len(inbox_emails)} inbox emails (excluded self-sent)")

# ── 6b. Thread dedup: group by normalized subject, keep latest ─────
def normalize_subject(subj):
    """Strip Re:/Fwd:/RE: prefixes and whitespace for thread grouping."""
    s = re.sub(r'^(Re:\s*|RE:\s*|Fwd:\s*|FW:\s*|Fw:\s*)+', '', subj, flags=re.IGNORECASE).strip()
    return s.lower()

threads = {}  # normalized_subject+account → latest email
for email in inbox_emails:
    v = email.get("values", {})
    subject = str(v.get("Subject", ""))
    account = str(v.get("Sync account", ""))
    date = str(v.get("Date", ""))
    
    thread_key = f"{normalize_subject(subject)}||{account}"
    
    if thread_key not in threads or date > str(threads[thread_key].get("values", {}).get("Date", "")):
        threads[thread_key] = email

deduped_emails = list(threads.values())
print(f"  After thread dedup: {len(deduped_emails)} unique threads")

# ── 6c. Classify each thread ──────────────────────────────────────
results = []
for email in deduped_emails:
    v = email.get("values", {})
    labels = str(v.get("Labels", ""))
    sender = str(v.get("From", ""))
    subject = str(v.get("Subject", ""))
    body = str(v.get("Text", ""))[:500]
    account = str(v.get("Sync account", ""))
    link = str(v.get("Link", ""))
    date = str(v.get("Date", ""))
    
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    body_lower = body.lower()
    
    # Extract domain from sender email
    domain = ""
    email_match = re.search(r'@([\w.-]+)', sender)
    if email_match:
        domain = email_match.group(1).lower()
    
    # Try rule match
    matched_rule = match_rules(sender_lower, domain, labels, subject_lower, body_lower)
    
    if matched_rule:
        priority = matched_rule["priority"]
        intent = matched_rule["action"]
        needs_task = matched_rule["needs_task"]
        reasons = [f"Rule: {matched_rule['name']}"]
        is_newsletter = intent in ("newsletter", "archive")
        entity_override = matched_rule.get("entity", "")
    else:
        # Fallback: contact-based classification
        priority = "Medium"
        intent = "fyi"
        needs_task = False
        reasons = ["No rule matched"]
        is_newsletter = False
        entity_override = ""
        
        contact_priority, contact_reason = check_contacts(sender_lower)
        if contact_priority:
            priority = contact_priority
            reasons = [contact_reason]
            if contact_priority == "High":
                # Refine intent based on content
                text_lower = (subject_lower + " " + body_lower)
                if any(w in text_lower for w in ["please", "can you", "could you", "need you to"]):
                    intent = "action_required"
                    needs_task = True
                elif "?" in subject or any(w in text_lower for w in ["what do you think", "your thoughts", "let me know"]):
                    intent = "reply_needed"
                    needs_task = True
                else:
                    intent = "fyi"
                    needs_task = True
    
    # Detect newsletter from unsubscribe link
    if "unsubscribe" in body_lower:
        is_newsletter = True
    
    # Archive intent means no task needed
    if intent == "archive":
        needs_task = False
    
    # Dedup check against existing tasks
    already_has_task = link in existing_threads
    if already_has_task:
        needs_task = False
    
    # Project mapping
    project = entity_override or ""
    if not project:
        account_lower = account.lower()
        for email_addr, proj in PROJECT_MAPPING.items():
            if email_addr in account_lower:
                project = proj
                break
    
    results.append({
        "from": sender,
        "subject": subject[:80],
        "account": account,
        "priority": priority,
        "intent": intent,
        "reasons": reasons,
        "is_newsletter": is_newsletter,
        "needs_task": needs_task,
        "link": link,
        "project": project,
    })


# ── 7. Output ───────────────────────────────────────────────────────
priorities = Counter(r["priority"] for r in results)
intents = Counter(r["intent"] for r in results)
accounts = Counter(r["account"] for r in results)
newsletters = sum(1 for r in results if r["is_newsletter"])
tasks = [r for r in results if r["needs_task"]]

print(f"\n{'='*80}")
print(f"EMAIL CLASSIFICATION v3 — {len(results)} inbox emails")
print(f"{'='*80}")
print(f"\nPriority: High={priorities['High']}  Medium={priorities['Medium']}  Low={priorities['Low']}")
print(f"Intents: {dict(intents)}")
print(f"Accounts: {dict(accounts)}")
print(f"Newsletters: {newsletters}")
print(f"Tasks to create: {len(tasks)} (max {MAX_TASKS})")

archive_results = [r for r in results if r["intent"] == "archive"]
active_results = [r for r in results if r["intent"] != "archive"]

for level in ["High", "Medium", "Low"]:
    level_results = [r for r in active_results if r["priority"] == level]
    if level_results:
        print(f"\n--- {level.upper()} PRIORITY ---")
        for r in level_results:
            flags = []
            if r["needs_task"]: flags.append("TASK")
            if r["is_newsletter"]: flags.append("UNSUB")
            flag_str = f" [{','.join(flags)}]" if flags else ""
            print(f"  [{r['intent'].upper()}]{flag_str} {r['from']}: {r['subject']}")
            if r["reasons"]:
                print(f"    → {', '.join(r['reasons'])}")

if archive_results:
    print(f"\n--- ARCHIVE ({len(archive_results)}) ---")
    for r in archive_results:
        print(f"  {r['from']}: {r['subject']}")
        if r["reasons"]:
            print(f"    → {', '.join(r['reasons'])}")

print(f"\nArchive: {len(archive_results)}  Active: {len(active_results)}")

# Save results (v3 format — also compatible with v2 consumer)
output = {
    "total": len(results),
    "results": results,
    "version": 3,
    "rules_loaded": total_rules,
}
with open("/home/user/workspace/email_classification_v3.json", "w") as f:
    json.dump(output, f, indent=2)

# Also write to v2 path for backward compat with cron
with open("/home/user/workspace/email_classification_v2.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved.")
