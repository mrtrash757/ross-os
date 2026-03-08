"""
Ross OS — Social Listener Self-Expanding Rule Suggester

After the social listener runs, this module analyzes found mentions
to suggest new listening rules based on recurring patterns:
- Frequently mentioned handles/entities not yet tracked
- Emerging hashtags in Ross's domain
- New companies/people appearing in aviation/VC discussions
- Competitor names detected in mentions

The suggestions are written to the Social Listening Rules table
with Active? = false so Ross can review and enable them.
"""

import json, subprocess, re
from collections import Counter, defaultdict
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

def coda_insert(table_id, rows):
    payload = json.dumps({"rows": rows, "keyColumns": ["Name"]})
    result = subprocess.run([
        "curl", "-s", "--max-time", "15", "-X", "POST",
        f"https://coda.io/apis/v1/docs/{DOC}/tables/{table_id}/rows",
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", "Content-Type: application/json",
        "-d", payload
    ], capture_output=True, text=True)
    return json.loads(result.stdout)

def suggest_rules(mentions_data):
    """
    Analyze a list of social mentions and suggest new listening rules.
    
    Args:
        mentions_data: list of dicts with keys: content, author_handle, platform, rule_name
    
    Returns:
        list of suggested rules (dicts)
    """
    # Load existing rules to avoid duplicates
    existing_rules = coda_get("grid-LNI2nlJZ3X")
    existing_queries = set()
    existing_names = set()
    for r in existing_rules:
        v = r.get("values", {})
        existing_queries.add(str(v.get("Query", "")).lower())
        existing_names.add(str(v.get("Name", "")).lower())
    
    # Load settings
    settings_raw = coda_get("grid-ybi2tIogls")
    settings = {s.get("values", {}).get("Key", ""): s.get("values", {}).get("Value", "") for s in settings_raw}
    
    auto_suggest = settings.get("social_auto_suggest_rules", "true").lower() == "true"
    threshold = int(settings.get("social_suggest_threshold", "3"))
    
    if not auto_suggest:
        print("Auto-suggest disabled in settings.")
        return []
    
    # Extract patterns from mentions
    handle_counter = Counter()
    hashtag_counter = Counter()
    entity_counter = Counter()
    
    # Ross's own handles to exclude
    ross_handles = {"@miaviationking", "@rosskinkade", "@asteriaair", "@asteriapartners", "@trashpandacap"}
    
    for mention in mentions_data:
        content = mention.get("content", "")
        author = mention.get("author_handle", "")
        
        # Extract @handles
        handles = re.findall(r'@\w+', content.lower())
        for h in handles:
            if h not in ross_handles:
                handle_counter[h] += 1
        
        # Track active authors
        if author and author.lower() not in ross_handles:
            handle_counter[f"@{author.lower()}"] += 1
        
        # Extract #hashtags
        hashtags = re.findall(r'#\w+', content.lower())
        for tag in hashtags:
            hashtag_counter[tag] += 1
        
        # Extract potential company/entity names (capitalized multi-word)
        entities = re.findall(r'(?<!\w)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?!\w)', content)
        for entity in entities:
            if entity.lower() not in existing_queries and len(entity) > 5:
                entity_counter[entity] += 1
    
    suggestions = []
    
    # Suggest rules for frequently mentioned handles
    for handle, count in handle_counter.most_common(10):
        if count >= threshold and handle not in existing_queries:
            clean_name = handle.replace("@", "")
            suggestion_name = f"Suggested: {clean_name} mentions"
            if suggestion_name.lower() not in existing_names:
                suggestions.append({
                    "name": suggestion_name,
                    "query": handle,
                    "platform": "X",
                    "category": "Market intel",
                    "entity": "Person",
                    "signal": "Mention",
                    "priority": "Medium",
                    "type": "Handle",
                    "frequency": "Weekly",
                    "reason": f"Mentioned {count} times in recent social data",
                })
    
    # Suggest rules for trending hashtags
    for tag, count in hashtag_counter.most_common(10):
        if count >= threshold and tag not in existing_queries:
            suggestion_name = f"Suggested: {tag} trend"
            if suggestion_name.lower() not in existing_names:
                suggestions.append({
                    "name": suggestion_name,
                    "query": tag,
                    "platform": "X",
                    "category": "Market intel",
                    "entity": "Topic",
                    "signal": "Other",
                    "priority": "Low",
                    "type": "Keyword",
                    "frequency": "Weekly",
                    "reason": f"Hashtag appeared {count} times in recent mentions",
                })
    
    # Suggest rules for recurring entities
    for entity, count in entity_counter.most_common(5):
        if count >= threshold:
            suggestion_name = f"Suggested: {entity} tracking"
            if suggestion_name.lower() not in existing_names:
                suggestions.append({
                    "name": suggestion_name,
                    "query": f'"{entity}"',
                    "platform": "X",
                    "category": "Market intel",
                    "entity": "Company",
                    "signal": "Mention",
                    "priority": "Medium",
                    "type": "Keyword",
                    "frequency": "Weekly",
                    "reason": f"Entity mentioned {count} times across mentions",
                })
    
    return suggestions

def write_suggestions_to_coda(suggestions):
    """Write suggested rules to Coda with Active? = false for Ross to review."""
    if not suggestions:
        print("No new rule suggestions to write.")
        return
    
    rows = []
    for s in suggestions:
        rows.append({
            "cells": [
                {"column": "Name", "value": s["name"]},
                {"column": "Platform", "value": s["platform"]},
                {"column": "Query", "value": s["query"]},
                {"column": "Active?", "value": False},  # Inactive until Ross approves
                {"column": "Frequency", "value": s["frequency"]},
                {"column": "Category", "value": s["category"]},
                {"column": "Entity", "value": s["entity"]},
                {"column": "Signal", "value": s["signal"]},
                {"column": "Priority", "value": s["priority"]},
                {"column": "Type", "value": s["type"]},
                {"column": "Notes", "value": f"Auto-suggested on {datetime.now().strftime('%Y-%m-%d')}\nReason: {s['reason']}"},
            ]
        })
    
    resp = coda_insert("grid-LNI2nlJZ3X", rows)
    print(f"Wrote {len(rows)} rule suggestions (inactive, pending Ross's review)")
    return resp


if __name__ == "__main__":
    # Demo: run with some sample mention data
    sample_mentions = [
        {"content": "Great to see @AsteriaAir expanding routes. @JetBlue should take notes. #aviation #regionalair", "author_handle": "avgeek42", "platform": "X"},
        {"content": "@MIAviationKing nailed it with the Part 135 analysis. @SurfAir @JSXAir competing hard", "author_handle": "flightaware_fan", "platform": "X"},
        {"content": "Big moves in regional aviation. @JetBlue @SurfAir @WheelsUp all pivoting. Ross Kinkade called this.", "author_handle": "airline_insider", "platform": "X"},
    ]
    
    suggestions = suggest_rules(sample_mentions)
    if suggestions:
        print(f"\n{len(suggestions)} rule suggestions generated:")
        for s in suggestions:
            print(f"  [{s['priority']}] {s['name']}: {s['query']} — {s['reason']}")
        # Don't write to Coda in demo mode
        # write_suggestions_to_coda(suggestions)
    else:
        print("No suggestions above threshold.")
