---
name: ross-os-calendar-io
description: Read and manage Ross's calendar events. Use this skill when you need to check today's schedule, find meeting times, create events, or sync calendar data to the Coda Calendar Mirror table. Uses the Gmail with Calendar connector and the Coda API for the mirror table.
metadata:
  author: ross-os
  version: '1.0'
  category: io
---

# Ross OS — Calendar IO Skill

## When to Use This Skill

Load this skill when you need to:
- Check Ross's schedule for today, this week, or a date range
- Find free time or scheduling conflicts
- Create, update, or delete calendar events
- Read the Calendar Mirror table in Coda
- Sync calendar data into Coda's Meetings & Events table
- Prepare meeting context (who's attending, what's the agenda)

## Data Sources

1. **Live calendar** — via the `gcal` connector (Gmail with Calendar). Real-time access.
2. **Calendar Mirror** in Coda (`grid-KqCsJ3ILm9`) — Synced snapshot for the Day view.
3. **Meetings & Events** in Coda (`grid-HRBNYX_9N1`) — Richer meeting data with contacts and type tagging.

## Connector: Gmail with Calendar

Source ID: `gcal`

### Search Calendar Events

Use `call_external_tool` with:

```json
{
  "tool_name": "search_calendar",
  "source_id": "gcal",
  "arguments": {
    "start_date": "2026-03-08T00:00:00-04:00",
    "end_date": "2026-03-08T23:59:59-04:00",
    "queries": [""]
  }
}
```

- Empty query `[""]` returns all events in the date range.
- Use keyword queries like `["standup", "sync"]` to find specific meetings.
- Ross is in **US Eastern Time** (EDT = UTC-4, EST = UTC-5).
- Use ISO 8601 format with timezone offset.

### Create a Calendar Event

```json
{
  "tool_name": "update_calendar",
  "source_id": "gcal",
  "arguments": {
    "create_actions": [{
      "action": "create",
      "title": "Coffee with Jane",
      "description": "Catch up on Asteria Air progress",
      "start_date_time": "2026-03-09T10:00:00-04:00",
      "end_date_time": "2026-03-09T10:30:00-04:00",
      "attendees": ["jane@example.com", "ross@trashpanda.capital"],
      "meeting_provider": null,
      "location": null
    }],
    "delete_actions": [],
    "update_actions": [],
    "user_prompt": null
  }
}
```

Set `meeting_provider` to `"google_meet"` or `"zoom"` to add a video link.

### Update a Calendar Event

```json
{
  "tool_name": "update_calendar",
  "source_id": "gcal",
  "arguments": {
    "create_actions": [],
    "delete_actions": [],
    "update_actions": [{
      "action": "update",
      "event_id": "{event_id_from_search}",
      "title": "Updated Title",
      "description": null,
      "start_date_time": null,
      "end_date_time": null,
      "attendees": null,
      "meeting_provider": null,
      "location": null
    }],
    "user_prompt": null
  }
}
```

Set fields to `null` to keep existing values.

### Delete a Calendar Event

```json
{
  "tool_name": "update_calendar",
  "source_id": "gcal",
  "arguments": {
    "create_actions": [],
    "delete_actions": [{
      "action": "delete",
      "event_id": "{event_id_from_search}"
    }],
    "update_actions": [],
    "user_prompt": null
  }
}
```

## Coda Calendar Tables

### Calendar Mirror (grid-KqCsJ3ILm9)

| Column | Type |
|--------|------|
| Name | text |
| Calendar | text |
| Date | text |
| Start time | time |
| End time | time |
| Location | text |
| Days | lookup |

### Meetings & Events (grid-HRBNYX_9N1)

| Column | Type |
|--------|------|
| Title | text |
| Day | lookup |
| Start time | text |
| Date | date |
| End time | text |
| Type | select (Work / Asteria / Personal) |
| Location Link | link |
| Related Contacts | lookup |

### Write to Coda Calendar Mirror

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-KqCsJ3ILm9/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Team Standup"},
        {"column": "Calendar", "value": "Work"},
        {"column": "Date", "value": "2026-03-08"},
        {"column": "Start time", "value": "09:00"},
        {"column": "End time", "value": "09:30"},
        {"column": "Location", "value": "Google Meet"}
      ]
    }],
    "keyColumns": ["Name", "Date"]
  }'
```

### Write to Meetings & Events

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HRBNYX_9N1/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Title", "value": "Coffee with Jane"},
        {"column": "Date", "value": "2026-03-09"},
        {"column": "Start time", "value": "10:00"},
        {"column": "End time", "value": "10:30"},
        {"column": "Type", "value": "Asteria"}
      ]
    }],
    "keyColumns": ["Title", "Date"]
  }'
```

## Common Recipes

### Get today's schedule

```python
# Use call_external_tool
search_calendar(
  start_date="2026-03-08T00:00:00-04:00",
  end_date="2026-03-08T23:59:59-04:00",
  queries=[""]
)
```

### Find free slots this week

Search all events for the week, then compute gaps between events during working hours (9am-6pm ET).

### Sync today's calendar to Coda

1. Fetch today's events via `search_calendar`
2. For each event, upsert into Calendar Mirror and/or Meetings & Events
3. Use `keyColumns: ["Name", "Date"]` or `["Title", "Date"]` for upsert behavior

## Ross's Timezone

- **Eastern Time** — EDT (UTC-4) Mar-Nov, EST (UTC-5) Nov-Mar
- Always include timezone offset in ISO dates
- Working hours assumption: 9:00 AM - 6:00 PM ET

## Error Handling

- **Connector errors:** If `search_calendar` fails, the gcal connector may need re-auth. Alert Ross.
- **Coda 429:** Rate limited. Wait 10 seconds, retry.
- **Stale mirror data:** If Calendar Mirror is out of date, run a sync from live calendar.
