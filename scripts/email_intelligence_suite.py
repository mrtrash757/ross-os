"""
Ross OS — Email Intelligence Suite
Covers:
1. Newsletter Kill List (unsubscribe candidates)
2. Response Queue (emails needing replies)  
3. Stale Comms Detection (contacts going cold)
4. Superhuman Split Inbox Rule Suggestions
"""

import json, subprocess, sys
from datetime import datetime, timedelta
from collections import Counter, defaultdict

TOKEN = "f8b53a89-6376-486e-85d8-f59fffed59d1"
DOC = "nSMMjxb_b2"

def coda_get(table_id, limit=500):
    result = subprocess.run([
        "curl", "-s", "--max-time", "20",
        f"https://coda.io/apis/v1/docs/{DOC}/tables/{table_id}/rows?useColumnNames=true&limit={limit}",
        "-H", f"Authorization: Bearer {TOKEN}"
    ], capture_output=True, text=True)
    return json.loads(result.stdout).get("items", [])

def coda_upsert(table_id, rows, key_columns=None):
    payload = {"rows": rows}
    if key_columns:
        payload["keyColumns"] = key_columns
    result = subprocess.run([
        "curl", "-s", "--max-time", "20", "-X", "POST",
        f"https://coda.io/apis/v1/docs/{DOC}/tables/{table_id}/rows",
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ], capture_output=True, text=True)
    return json.loads(result.stdout)

# ============================================================
# LOAD DATA
# ============================================================
print("Loading data...")
emails = coda_get("grid-sync-1004-Email", 500)
contacts = coda_get("grid-1M2UOaliIC", 500)
interactions = coda_get("grid-bDW7PytKOq", 500)
settings_raw = coda_get("grid-ybi2tIogls", 200)

settings = {}
for s in settings_raw:
    v = s.get("values", {})
    settings[v.get("Key", "")] = v.get("Value", "")

def csv_list(key):
    return [x.strip().lower() for x in settings.get(key, "").split(",") if x.strip()]

NEWSLETTER_SENDERS = csv_list("email_newsletter_senders")
LOW_SENDERS = csv_list("email_low_senders")
DIGEST_SENDERS = csv_list("email_digest_senders")

print(f"  {len(emails)} emails, {len(contacts)} contacts, {len(interactions)} interactions")

# ============================================================
# 1. NEWSLETTER KILL LIST
# ============================================================
print(f"\n{'='*70}")
print("1. NEWSLETTER KILL LIST — Unsubscribe Candidates")
print(f"{'='*70}")

newsletter_frequency = defaultdict(lambda: {"count": 0, "subjects": [], "accounts": set(), "method": set()})

for e in emails:
    v = e.get("values", {})
    sender = str(v.get("From", ""))
    subject = str(v.get("Subject", ""))[:80]
    account = str(v.get("Sync account", ""))
    labels = str(v.get("Labels", ""))
    body = str(v.get("Text", ""))[:1000].lower()
    sender_lower = sender.lower()
    
    is_newsletter = False
    method = set()
    
    # Check if known newsletter sender
    if any(ns in sender_lower for ns in NEWSLETTER_SENDERS):
        is_newsletter = True
        method.add("known_sender")
    
    # Check Superhuman Marketing label
    if "[Superhuman]/AI/Marketing" in labels:
        is_newsletter = True
        method.add("sh_marketing")
    
    # Check promotions category
    if "CATEGORY_PROMOTIONS" in labels:
        is_newsletter = True
        method.add("gmail_promo")
    
    # Check body for unsubscribe
    if any(kw in body for kw in ["unsubscribe", "opt out", "opt-out", "email preferences", "manage your subscription"]):
        is_newsletter = True
        method.add("unsub_body")
    
    # Check Superhuman News label (news digests)
    if "[Superhuman]/AI/News" in labels:
        is_newsletter = True
        method.add("sh_news")
    
    if is_newsletter:
        newsletter_frequency[sender]["count"] += 1
        newsletter_frequency[sender]["subjects"].append(subject)
        newsletter_frequency[sender]["accounts"].add(account)
        newsletter_frequency[sender]["method"].update(method)

# Sort by frequency (most emails = most annoying)
kill_list = sorted(newsletter_frequency.items(), key=lambda x: x[1]["count"], reverse=True)

print(f"\nFound {len(kill_list)} newsletter senders ({sum(v['count'] for _, v in kill_list)} total emails)")
print(f"\n{'Sender':<30} {'Count':>5}  {'Detection':>25}  Account(s)")
print("-" * 95)
kill_list_output = []
for sender, data in kill_list:
    methods = ", ".join(sorted(data["method"]))
    accounts = ", ".join(sorted(data["accounts"]))
    print(f"{sender:<30} {data['count']:>5}  {methods:>25}  {accounts}")
    kill_list_output.append({
        "sender": sender,
        "email_count": data["count"],
        "detection_methods": list(data["method"]),
        "accounts": list(data["accounts"]),
        "sample_subjects": data["subjects"][:3],
        "already_in_settings": any(ns in sender.lower() for ns in NEWSLETTER_SENDERS),
    })

# Flag senders NOT yet in settings (need to be added)
uncaught = [k for k in kill_list_output if not k["already_in_settings"]]
if uncaught:
    print(f"\n⚠ {len(uncaught)} senders NOT yet in email_newsletter_senders setting:")
    for k in uncaught:
        print(f"  → {k['sender']} ({k['email_count']} emails, detected via: {', '.join(k['detection_methods'])})")

# ============================================================
# 2. RESPONSE QUEUE — Emails Needing Replies
# ============================================================
print(f"\n{'='*70}")
print("2. RESPONSE QUEUE — Emails Needing Your Reply")
print(f"{'='*70}")

response_queue = []
for e in emails:
    v = e.get("values", {})
    labels = str(v.get("Labels", ""))
    sender = str(v.get("From", ""))
    subject = str(v.get("Subject", ""))[:80]
    account = str(v.get("Sync account", ""))
    date = str(v.get("Date", ""))
    body = str(v.get("Text", ""))[:500].lower()
    link = str(v.get("Link", ""))
    sender_lower = sender.lower()
    
    # Skip Ross's own sent messages
    if sender_lower.startswith("ross"):
        continue
    
    # Skip known newsletters, low senders, and marketing emails
    is_known_newsletter = any(ns in sender_lower for ns in NEWSLETTER_SENDERS)
    is_known_low = any(ls in sender_lower for ls in LOW_SENDERS)
    is_marketing = "[Superhuman]/AI/Marketing" in labels
    is_promo = "CATEGORY_PROMOTIONS" in labels
    if is_known_newsletter or is_known_low or is_marketing or is_promo:
        continue
    
    needs_reply = False
    urgency = "normal"
    signals = []
    
    # Superhuman Respond label
    if "[Superhuman]/AI/Respond" in labels:
        needs_reply = True
        signals.append("Superhuman: Respond")
        if "UNREAD" in labels:
            urgency = "high"
            signals.append("still unread")
    
    # Superhuman Waiting (Ross is the one waiting — others need to respond, but maybe Ross needs to follow up)
    if "[Superhuman]/AI/Waiting" in labels:
        # This means someone else needs to respond — surface as "follow up" candidate
        if "UNREAD" not in labels:  # Ross read it but is waiting
            signals.append("waiting for reply")
    
    # Direct questions in subject
    if "?" in str(v.get("Subject", "")):
        if "UNREAD" in labels:
            needs_reply = True
            signals.append("question in subject")
    
    # Action language in body
    if any(phrase in body for phrase in ["can you", "could you", "would you", "please", "need you to", 
                                          "your thoughts", "what do you think", "let me know"]):
        if "UNREAD" in labels:
            needs_reply = True
            signals.append("action language")
    
    if needs_reply:
        response_queue.append({
            "sender": sender,
            "subject": subject,
            "account": account,
            "date": date,
            "urgency": urgency,
            "signals": signals,
            "link": link,
            "is_unread": "UNREAD" in labels,
        })

# Sort: high urgency first, then by date
response_queue.sort(key=lambda x: (0 if x["urgency"] == "high" else 1, x["date"]))

print(f"\n{len(response_queue)} emails need your response:")
for i, r in enumerate(response_queue, 1):
    urgency_flag = "🔴" if r["urgency"] == "high" else "🟡"
    unread_flag = " [UNREAD]" if r["is_unread"] else ""
    print(f"  {i}. {urgency_flag} {r['sender']}: {r['subject']}")
    print(f"     {r['account']} | {r['date'][:10]} | {', '.join(r['signals'])}{unread_flag}")

# ============================================================
# 3. STALE COMMS DETECTION
# ============================================================
print(f"\n{'='*70}")
print("3. STALE COMMS — Contacts Going Cold")
print(f"{'='*70}")

# Build a map of last email from each contact
contact_list = []
for c in contacts:
    v = c.get("values", {})
    name = v.get("Name", "").strip()
    if not name:
        continue
    contact_list.append({
        "name": name,
        "org": v.get("Org", ""),
        "importance": v.get("Importance", ""),
        "cadence": v.get("Cadence", ""),
        "next_touch": v.get("Next touch date", ""),
        "channels": v.get("Channels", ""),
    })

# Build email activity per sender
sender_last_email = defaultdict(lambda: {"last_date": "", "count": 0, "accounts": set()})
for e in emails:
    v = e.get("values", {})
    sender = str(v.get("From", "")).strip()
    date = str(v.get("Date", ""))
    account = str(v.get("Sync account", ""))
    
    if sender and date:
        if date > sender_last_email[sender]["last_date"]:
            sender_last_email[sender]["last_date"] = date
        sender_last_email[sender]["count"] += 1
        sender_last_email[sender]["accounts"].add(account)

# Also check interactions table
interaction_contacts = defaultdict(lambda: {"last_date": "", "count": 0})
for i in interactions:
    v = i.get("values", {})
    contact = str(v.get("Contact", "")).strip()
    date = str(v.get("Date", ""))
    if contact and date:
        if date > interaction_contacts[contact]["last_date"]:
            interaction_contacts[contact]["last_date"] = date
        interaction_contacts[contact]["count"] += 1

print(f"\nContacts ({len(contact_list)} total):")
today = datetime.now()
stale_contacts = []

for c in contact_list:
    name = c["name"]
    cadence_days = int(c["cadence"]) if c["cadence"] and str(c["cadence"]).isdigit() else 0
    
    # Find last email activity (fuzzy match sender to contact name)
    last_email = None
    email_count = 0
    for sender, data in sender_last_email.items():
        if name.lower() in sender.lower() or sender.lower() in name.lower():
            if not last_email or data["last_date"] > last_email:
                last_email = data["last_date"]
            email_count += data["count"]
    
    # Check interactions too
    last_interaction = interaction_contacts.get(name, {}).get("last_date", "")
    interaction_count = interaction_contacts.get(name, {}).get("count", 0)
    
    # Determine last contact overall
    last_contact_date = max(last_email or "", last_interaction or "")
    
    days_since = None
    is_stale = False
    if last_contact_date:
        try:
            last_dt = datetime.fromisoformat(last_contact_date.replace("Z", "+00:00").split("+")[0].split("T")[0])
            days_since = (today - last_dt).days
            if cadence_days > 0 and days_since > cadence_days:
                is_stale = True
        except:
            pass
    else:
        is_stale = True  # Never contacted = stale by definition
    
    status = "STALE" if is_stale else "ok"
    stale_contacts.append({
        "name": name,
        "org": c["org"],
        "importance": c["importance"],
        "cadence_days": cadence_days,
        "days_since_contact": days_since,
        "last_email_date": last_email,
        "email_count": email_count,
        "last_interaction_date": last_interaction,
        "interaction_count": interaction_count,
        "is_stale": is_stale,
    })
    
    days_str = f"{days_since}d ago" if days_since is not None else "never"
    cadence_str = f"every {cadence_days}d" if cadence_days else "no cadence"
    print(f"  {'⚠ STALE' if is_stale else '  ok  '} {name} ({c['importance']}) — last contact: {days_str}, cadence: {cadence_str}, emails: {email_count}")

# ============================================================
# 4. SUPERHUMAN SPLIT INBOX RULES
# ============================================================
print(f"\n{'='*70}")
print("4. SUPERHUMAN SPLIT INBOX RULE SUGGESTIONS")
print(f"{'='*70}")

# Analyze patterns to suggest Gmail filters / Superhuman splits
sender_patterns = defaultdict(lambda: {"count": 0, "labels": set(), "categories": set(), "accounts": set(), "is_newsletter": False})

for e in emails:
    v = e.get("values", {})
    sender = str(v.get("From", ""))
    labels = str(v.get("Labels", ""))
    account = str(v.get("Sync account", ""))
    
    sender_patterns[sender]["count"] += 1
    sender_patterns[sender]["accounts"].add(account)
    
    for label in labels.split(","):
        label = label.strip()
        if label and label not in ["UNREAD", "INBOX", "IMPORTANT", "SENT", "STARRED"]:
            sender_patterns[sender]["labels"].add(label)
    
    for cat in ["CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_UPDATES", "CATEGORY_FORUMS"]:
        if cat in labels:
            sender_patterns[sender]["categories"].add(cat)

# Generate rule suggestions
rules = []

# Rule 1: High-volume senders that should have their own split
print("\n--- High-Volume Sender Splits ---")
for sender, data in sorted(sender_patterns.items(), key=lambda x: x[1]["count"], reverse=True):
    if data["count"] >= 3 and sender.lower() not in ["ross kinkade", "reminder"]:
        suggested_split = None
        if any(ns in sender.lower() for ns in NEWSLETTER_SENDERS):
            suggested_split = "Newsletters"
        elif any(ns in sender.lower() for ns in DIGEST_SENDERS):
            suggested_split = "Digests"
        elif "enilria" in sender.lower():
            suggested_split = "Aviation Intel"
        elif "CATEGORY_PROMOTIONS" in str(data.get("categories", "")):
            suggested_split = "Promotions"
        
        if suggested_split:
            rules.append({
                "type": "split",
                "sender": sender,
                "suggested_split": suggested_split,
                "email_count": data["count"],
                "accounts": list(data["accounts"]),
            })
            print(f"  {sender} ({data['count']} emails) → Split: {suggested_split}")

# Rule 2: Category-based auto-labels
print("\n--- Category-Based Auto-Label Suggestions ---")
category_rules = {
    "CATEGORY_PROMOTIONS": {"split": "Promotions", "action": "Skip inbox, label Promo"},
    "CATEGORY_SOCIAL": {"split": "Social", "action": "Keep in inbox, label Social"},
}
for cat, rule in category_rules.items():
    count = sum(1 for e in emails if cat in str(e.get("values", {}).get("Labels", "")))
    if count > 0:
        rules.append({
            "type": "category_filter",
            "category": cat,
            "suggested_action": rule["action"],
            "split": rule["split"],
            "email_count": count,
        })
        print(f"  {cat}: {count} emails → {rule['action']}")

# Rule 3: Sender-specific suggestions
print("\n--- Sender-Specific Rule Suggestions ---")
service_senders = defaultdict(int)
for e in emails:
    v = e.get("values", {})
    sender = str(v.get("From", ""))
    sender_lower = sender.lower()
    
    if any(svc in sender_lower for svc in ["reminder", "attio", "salesforce", "github", "supabase", "coda"]):
        service_senders[sender] += 1

for sender, count in sorted(service_senders.items(), key=lambda x: x[1], reverse=True):
    rules.append({
        "type": "service_filter",
        "sender": sender,
        "suggested_action": "Auto-label as Tools/Services, skip inbox unless error",
        "email_count": count,
    })
    print(f"  {sender} ({count}) → Label: Tools/Services, skip inbox")

# ============================================================
# SAVE ALL OUTPUT
# ============================================================
output = {
    "generated": datetime.now().isoformat(),
    "newsletter_kill_list": kill_list_output,
    "response_queue": response_queue,
    "stale_contacts": stale_contacts,
    "superhuman_rules": rules,
    "summary": {
        "newsletters_detected": len(kill_list_output),
        "total_newsletter_emails": sum(k["email_count"] for k in kill_list_output),
        "uncaught_newsletters": len(uncaught),
        "emails_needing_response": len(response_queue),
        "total_contacts": len(contact_list),
        "stale_contacts": sum(1 for c in stale_contacts if c["is_stale"]),
        "rule_suggestions": len(rules),
    }
}

with open("/home/user/workspace/email_intelligence_output.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"  Newsletter senders found: {output['summary']['newsletters_detected']}")
print(f"  Total newsletter emails: {output['summary']['total_newsletter_emails']}")
print(f"  Uncaught (need settings update): {output['summary']['uncaught_newsletters']}")
print(f"  Emails needing response: {output['summary']['emails_needing_response']}")
print(f"  Contacts tracked: {output['summary']['total_contacts']}")
print(f"  Stale contacts: {output['summary']['stale_contacts']}")
print(f"  Superhuman rule suggestions: {output['summary']['rule_suggestions']}")
print(f"\nSaved to email_intelligence_output.json")
