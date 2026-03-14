#!/usr/bin/env python3
"""
fetch_listening_rules.py
Exports active Social Listening Rules from Coda to listening_rules.json
for the Content Pipeline cron agent to consume.
"""

import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

# ── Credentials ───────────────────────────────────────────────────────────────
CODA_TOKEN = "f8b53a89-6376-486e-85d8-f59fffed59d1"
CODA_DOC   = "nSMMjxb_b2"
TABLE_ID   = "grid-LNI2nlJZ3X"
OUTPUT_FILE = "/home/user/workspace/listening_rules.json"
TZ = ZoneInfo("America/Detroit")

HEADERS = {"Authorization": f"Bearer {CODA_TOKEN}"}
BASE_URL = f"https://coda.io/apis/v1/docs/{CODA_DOC}/tables/{TABLE_ID}/rows"


def fetch_all_rows() -> list[dict]:
    """Fetch every row from the Social Listening Rules table with pagination."""
    rows = []
    url = BASE_URL
    params = {"useColumnNames": "true", "limit": 100}

    print("📡 Fetching Social Listening Rules from Coda...")

    while url:
        for attempt in range(1, 4):
            resp = requests.get(url, headers=HEADERS, params=params if url == BASE_URL else None)

            if resp.status_code == 200:
                data = resp.json()
                page_rows = data.get("items", [])
                rows.extend(page_rows)
                print(f"   ↳ Fetched {len(page_rows)} rows (total so far: {len(rows)})")
                url = data.get("nextPageLink")
                break

            elif resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                print(f"⏳ Rate limited — waiting {wait}s (attempt {attempt}/3)...")
                time.sleep(wait)

            else:
                print(f"❌ Unexpected status {resp.status_code}: {resp.text}")
                resp.raise_for_status()
        else:
            raise RuntimeError("Exceeded retry limit due to rate limiting.")

    return rows


def is_active(values: dict) -> bool:
    """Return True if the row's Active? field is truthy."""
    active = values.get("Active?")
    if isinstance(active, bool):
        return active
    if isinstance(active, str):
        return active.strip().lower() in ("true", "yes", "active", "1")
    return bool(active)


def extract_rule(values: dict) -> dict:
    """Extract relevant fields from a row's values dict."""
    return {
        "name":     values.get("Name", "").strip(),
        "query":    values.get("Query", "").strip(),
        "keywords": values.get("Notes", "").strip(),   # Notes used as keywords field
        "category": values.get("Category", "").strip(),
        "type":     values.get("Type", "").strip(),
        "priority": values.get("Priority", "").strip(),
        "frequency": values.get("Frequency", "").strip(),
    }


def main():
    all_rows = fetch_all_rows()
    print(f"\n✅ Total rows fetched: {len(all_rows)}")

    # Filter to active rules only
    active_rows = [r for r in all_rows if is_active(r.get("values", {}))]
    print(f"🔍 Active rules: {len(active_rows)}")

    # Group by platform
    rules_by_platform: dict[str, list[dict]] = {}
    for row in active_rows:
        values   = row.get("values", {})
        platform = values.get("Platform", "Unknown").strip()
        rule     = extract_rule(values)
        rules_by_platform.setdefault(platform, []).append(rule)

    # Log breakdown
    for platform, rules in sorted(rules_by_platform.items()):
        print(f"   📌 {platform}: {len(rules)} rules")

    output = {
        "fetched_at":        datetime.now(tz=TZ).isoformat(),
        "total_rules":       len(active_rows),
        "rules_by_platform": rules_by_platform,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Saved to {OUTPUT_FILE}")
    print(f"🎉 Done — {len(active_rows)} active rules across {len(rules_by_platform)} platform(s).")


if __name__ == "__main__":
    main()
