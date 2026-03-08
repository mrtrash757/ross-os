import json, subprocess, re
from datetime import datetime

TOKEN = "f8b53a89-6376-486e-85d8-f59fffed59d1"
DOC = "nSMMjxb_b2"

def coda_get(table_id, limit=200):
    result = subprocess.run([
        "curl", "-s", "--max-time", "15",
        f"https://coda.io/apis/v1/docs/{DOC}/tables/{table_id}/rows?useColumnNames=true&limit={limit}",
        "-H", f"Authorization: Bearer {TOKEN}"
    ], capture_output=True, text=True)
    return json.loads(result.stdout).get("items", [])

# 1. Load Settings
print("Loading settings...")
settings_raw = coda_get("grid-ybi2tIogls")
settings = {}
for s in settings_raw:
    v = s.get("values", {})
    settings[v.get("Key", "")] = v.get("Value", "")

def csv_list(key):
    """Get a setting as a lowercase list"""
    return [x.strip().lower() for x in settings.get(key, "").split(",") if x.strip()]

HIGH_SENDERS = csv_list("email_high_senders")
LOW_SENDERS = csv_list("email_low_senders")
NEWSLETTER_SENDERS = csv_list("email_newsletter_senders")
HIGH_DOMAINS = csv_list("email_high_domains")
URGENT_KEYWORDS = csv_list("email_urgent_keywords")
LEGAL_FINANCE_KEYWORDS = csv_list("email_legal_finance_keywords")
DIGEST_SENDERS = csv_list("email_digest_senders")
SKIP_TASK_INTENTS = csv_list("email_skip_task_intents")
MAX_TASKS = int(settings.get("email_max_tasks_per_run", "10"))

print(f"  High senders: {HIGH_SENDERS}")
print(f"  Newsletter senders: {NEWSLETTER_SENDERS}")
print(f"  Low senders: {LOW_SENDERS}")

# 2. Load contacts
print("Loading contacts...")
contacts_raw = coda_get("grid-1M2UOaliIC")
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

# 3. Load existing tasks for dedup
existing_tasks = coda_get("grid-7IWNsZiHzE")
existing_threads = set()
for t in existing_tasks:
    v = t.get("values", {})
    link = v.get("Thread ID link", "")
    if link:
        existing_threads.add(link)

# 4. Load emails
print("Loading emails...")
emails = coda_get("grid-sync-1004-Email")
print(f"  {len(emails)} emails")

# 5. Classify
results = []
for email in emails:
    v = email.get("values", {})
    labels = str(v.get("Labels", ""))
    sender = str(v.get("From", ""))
    subject = str(v.get("Subject", ""))
    body = str(v.get("Text", ""))[:500]
    account = str(v.get("Sync account", ""))
    link = str(v.get("Link", ""))
    date = str(v.get("Date", ""))
    
    if "UNREAD" not in labels:
        continue
    
    sender_lower = sender.lower()
    text_lower = (subject + " " + body).lower()
    priority = "Medium"
    intent = "fyi"
    reasons = []
    is_newsletter = False
    
    # --- Superhuman labels ---
    sh_respond = "[Superhuman]/AI/Respond" in labels
    sh_waiting = "[Superhuman]/AI/Waiting" in labels
    sh_meeting = "[Superhuman]/AI/Meeting" in labels
    sh_marketing = "[Superhuman]/AI/Marketing" in labels
    sh_news = "[Superhuman]/AI/News" in labels
    sh_ru = "[Superhuman]/ru" in labels
    
    # --- STEP 1: Check newsletter/low senders FIRST (before boosting) ---
    sender_subject_lower = (sender_lower + " " + subject.lower()).strip()
    is_known_newsletter = any(ns in sender_lower for ns in NEWSLETTER_SENDERS)
    # Low senders: match against sender OR sender+subject combo
    # This handles cases like "Google" + "Security alert" matching "google security"
    is_known_low = any(ls in sender_lower for ls in LOW_SENDERS) or \
                   any(ls in sender_subject_lower for ls in LOW_SENDERS if len(ls.split()) > 1)
    is_known_digest = any(ds in sender_lower for ds in DIGEST_SENDERS)
    
    if is_known_newsletter or (sh_marketing and not sh_respond):
        priority = "Low"
        intent = "newsletter"
        is_newsletter = True
        reasons.append("known newsletter" if is_known_newsletter else "marketing label")
    elif is_known_low:
        priority = "Low"
        intent = "notification"
        reasons.append("known low sender")
    elif is_known_digest:
        priority = "Medium"
        intent = "fyi"
        reasons.append("digest sender")
    else:
        # --- STEP 2: High priority signals (only if not newsletter/low) ---
        
        # Settings-driven high senders
        is_high_sender = any(hs in sender_lower for hs in HIGH_SENDERS)
        if is_high_sender:
            priority = "High"
            intent = "fyi"  # will refine below
            reasons.append("high priority sender")
        
        # VIP from contacts
        matched_contact = None
        for cname, cdata in contacts.items():
            if cname in sender_lower or sender_lower in cname:
                matched_contact = cdata
                if cdata["importance"] == "High":
                    priority = "High"
                    reasons.append("VIP contact")
                elif priority != "High":
                    priority = "Medium"
                    reasons.append("known contact")
                break
        
        # Superhuman Respond = always High
        if sh_respond:
            priority = "High"
            intent = "reply_needed"
            reasons.append("Superhuman: Respond")
        
        # Urgent keywords
        if any(kw in text_lower for kw in URGENT_KEYWORDS):
            priority = "High"
            reasons.append("urgent keyword")
        
        # Legal/finance — use PHRASE matching (not single words)
        if any(kw in text_lower for kw in LEGAL_FINANCE_KEYWORDS):
            priority = "High"
            reasons.append("legal/finance keyword")
        
        # Superhuman Meeting
        if sh_meeting:
            intent = "scheduling"
            if priority == "Low":
                priority = "Medium"
            reasons.append("Superhuman: Meeting")
        
        # Superhuman News (only downgrade if no other high signal)
        if sh_news and not any(r in reasons for r in ["high priority sender", "VIP contact", "Superhuman: Respond"]):
            if priority != "High":
                priority = "Low"
                intent = "fyi"
                reasons.append("Superhuman: News")
        
        # Promotions category
        if "CATEGORY_PROMOTIONS" in labels and priority != "High":
            priority = "Low"
            intent = "newsletter"
            is_newsletter = True
            reasons.append("promotions category")
    
    # Detect unsubscribe in body
    if "unsubscribe" in body.lower():
        is_newsletter = True
    
    # --- STEP 3: Refine intent for High priority ---
    if priority == "High" and intent == "fyi":
        if any(w in text_lower for w in ["please", "can you", "could you", "need you to"]):
            intent = "action_required"
        elif "?" in subject or any(w in text_lower for w in ["what do you think", "your thoughts", "let me know"]):
            intent = "reply_needed"
        else:
            intent = "fyi"  # high priority but informational (like Enilria reports)
    
    # Check dedup
    already_has_task = link in existing_threads
    needs_task = intent not in SKIP_TASK_INTENTS and not already_has_task
    
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
    })

# 6. Output
from collections import Counter
priorities = Counter(r["priority"] for r in results)
intents = Counter(r["intent"] for r in results)
accounts = Counter(r["account"] for r in results)
newsletters = sum(1 for r in results if r["is_newsletter"])
tasks = [r for r in results if r["needs_task"]]

print(f"\n{'='*80}")
print(f"EMAIL CLASSIFICATION v2 — {len(results)} unread emails")
print(f"{'='*80}")
print(f"\nPriority: High={priorities['High']}  Medium={priorities['Medium']}  Low={priorities['Low']}")
print(f"Intents: {dict(intents)}")
print(f"Accounts: {dict(accounts)}")
print(f"Newsletters: {newsletters}")
print(f"Tasks to create: {len(tasks)} (max {MAX_TASKS})")

for level in ["High", "Medium", "Low"]:
    print(f"\n--- {level.upper()} PRIORITY ---")
    for r in results:
        if r["priority"] == level:
            flags = []
            if r["needs_task"]: flags.append("TASK")
            if r["is_newsletter"]: flags.append("UNSUB")
            flag_str = f" [{','.join(flags)}]" if flags else ""
            print(f"  [{r['intent'].upper()}]{flag_str} {r['from']}: {r['subject']}")
            if r["reasons"]:
                print(f"    → {', '.join(r['reasons'])}")

with open("/home/user/workspace/email_classification_v2.json", "w") as f:
    json.dump({"total": len(results), "results": results}, f, indent=2)
