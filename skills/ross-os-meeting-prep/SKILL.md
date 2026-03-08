---
name: ross-os-meeting-prep
description: Automated meeting prep for Ross OS. Peeks at upcoming calendar events, researches attendees against Contacts table, recent emails, and web data, then delivers a briefing. Use when the morning brief runs, Ross says "prep me for meetings," or the night before a meeting-heavy day.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
---

# Ross OS — Meeting Prep

## When to Use This Skill

Load this skill when:
- The morning brief needs meeting context
- Ross says "prep me for my meetings" or "what do I have tomorrow"
- A calendar event is coming up within 2 hours (real-time prep)
- Ross asks about a specific person before a meeting

## Overview

Meeting Prep pulls from multiple data sources to build a briefing for each upcoming meeting:
1. Calendar events (via gcal connector)
2. Attendee lookup in Contacts table
3. Recent email threads with attendees
4. Fireflies meeting transcripts (if available)
5. Web research on unknown attendees

## Data Sources

| Source | How to Access | Purpose |
|--------|---------------|---------|
| Google Calendar | `search_calendar` (source_id: gcal) | Get events with attendees |
| Contacts | Coda `grid-1M2UOaliIC` | Known contact info, importance, notes |
| Messages | Coda `grid-sync-1004-Email` | Recent email threads with attendees |
| Interactions | Coda `grid-bDW7PytKOq` | Past interaction history |
| Fireflies | `fireflies_search` / `fireflies_get_summary` | Past meeting transcripts/notes |
| Meetings Events | Coda `grid-HRBNYX_9N1` | Write prep notes back to Coda |

**Coda API Token:** `f8b53a89-6376-486e-85d8-f59fffed59d1`  
**Coda Doc:** `nSMMjxb_b2`

## Instructions

### Step 1: Get Upcoming Calendar Events

Fetch events for the target date (usually tomorrow, or today if morning):

```
search_calendar(
  source_id="gcal",
  start_date="YYYY-MM-DDT00:00:00-04:00",  # Ross is America/Detroit (ET)
  end_date="YYYY-MM-DDT23:59:59-04:00",
  queries=[""]  # empty string = all events
)
```

Filter for events that:
- Have external attendees (not just Ross)
- Are not "Focus Time", "Lunch", or other personal blocks
- Are not cancelled

### Step 2: For Each Meeting, Research Attendees

For each meeting with external attendees:

#### 2a. Check Contacts Table
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true&limit=500" \
  -H "Authorization: Bearer f8b53a89-6376-486e-85d8-f59fffed59d1"
```
Match attendee email/name against contacts. Extract: Name, Org, Role, Importance, Notes, Last touch date.

#### 2b. Check Recent Emails
Search the Messages table for emails from/to each attendee in the last 30 days:
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-sync-1004-Email/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer f8b53a89-6376-486e-85d8-f59fffed59d1"
```
Filter by sender/recipient matching. Extract last 3 email subjects and key points.

#### 2c. Check Fireflies for Past Meetings
```
fireflies_search(query="keyword:attendee_name")
```
If found, pull the summary:
```
fireflies_get_summary(transcriptId=ID, fields=["overview", "action_items", "keywords"])
```

#### 2d. Web Research (for unknown attendees)
If an attendee is NOT in Contacts and NOT found in email history:
- Search LinkedIn (via search_vertical with vertical="people")
- Search web for "[Name] [Company]"
- Extract: role, company, recent news, shared connections

### Step 3: Build the Briefing

For each meeting, compose a briefing block:

```
## [Meeting Title] — [Time]
Location: [link or room]
Duration: [X min]

### Attendees
• [Name] — [Role], [Company] (Importance: [H/M/L])
  Last contact: [date] | Emails: [N in last 30d]
  Key context: [1-2 sentences from recent emails or Fireflies]

• [Name] — [Role], [Company] (NEW — not in Contacts)
  LinkedIn: [link]
  About: [1-2 sentences from web research]

### Meeting Context
- Previous meetings: [count from Fireflies, key takeaways]
- Recent email threads: [subjects]
- Open action items: [from Fireflies or email]

### Suggested Talking Points
1. [Based on email threads and past meetings]
2. [Based on attendee's recent activity]
3. [Based on open tasks/follow-ups]
```

### Step 4: Write to Meetings Events Table (Optional)

If the meeting doesn't exist in Meetings Events table, create a row:
```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HRBNYX_9N1/rows" \
  -H "Authorization: Bearer f8b53a89-6376-486e-85d8-f59fffed59d1" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Title", "value": "[Meeting title]"},
        {"column": "Date", "value": "YYYY-MM-DD"},
        {"column": "Start time", "value": "HH:MM AM/PM"},
        {"column": "End time", "value": "HH:MM AM/PM"},
        {"column": "Type", "value": "Work|Asteria|Personal"},
        {"column": "Location Link", "value": "[zoom/meet URL]"},
        {"column": "Notes", "value": "[prep briefing content]"}
      ]
    }]
  }'
```

### Step 5: Deliver the Briefing

If running as part of the morning brief → include in the notification body.
If running standalone → send as its own notification titled "Meeting Prep: [Date]".

## Integration Points

- **Morning Brief**: The morning brief skill should call meeting prep for today's meetings and include the output in the Schedule section.
- **EOD Debrief**: After meetings, the debrief can reference prep notes to check if action items were addressed.
- **Email Monitor**: If a high-priority email comes in from a meeting attendee, cross-reference with upcoming meetings.

## Error Handling

- No upcoming meetings → Skip silently
- Attendee not in Contacts → Do web research, suggest adding to Contacts
- Fireflies has no matching meetings → Skip that section
- Calendar API unavailable → Log error, skip meeting prep
