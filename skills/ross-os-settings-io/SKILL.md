---
name: ross-os-settings-io
description: Read Ross OS configuration from the Settings table in Coda. Use this skill at the start of any workflow skill to check if the skill is enabled, read schedule times, thresholds, and notification preferences. This is the control panel for the entire system.
metadata:
  author: ross-os
  version: '1.0'
  category: io
---

# Ross OS — Settings IO Skill

## When to Use This Skill

Load this skill when you need to:
- Check if a skill is enabled before running it
- Read schedule times (morning brief, EOD debrief, listener intervals)
- Get threshold values (stale contact days, fire scan cutoffs)
- Check notification preferences (quiet hours, detail level)
- Read system config (timezone, email)

Every workflow skill should load this at the start and respect the settings.

## Settings Table

- **Table ID:** `grid-ybi2tIogls`
- **Doc ID:** `nSMMjxb_b2`
- **API Token:** `${CODA_API_TOKEN}`

## Reading Settings

### Get all settings (recommended — one API call)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-ybi2tIogls/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Parse into a key-value map in your script:

```python
import json, subprocess

result = subprocess.run([
    'curl', '-s',
    'https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-ybi2tIogls/rows?useColumnNames=true&limit=100',
    '-H', 'Authorization: Bearer ${CODA_API_TOKEN}'
], capture_output=True, text=True)

data = json.loads(result.stdout)
settings = {}
for row in data.get('items', []):
    v = row.get('values', {})
    key = v.get('Key', row.get('name', ''))
    if key:
        settings[key] = v.get('Value', '')

# Now use: settings['morning_brief_enabled'], settings['stale_contact_red_days'], etc.
```

### Get a single setting by key

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-ybi2tIogls/rows?useColumnNames=true&query=Key:morning_brief_enabled" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

## Settings Registry

### Schedule Settings

| Key | Default | Description |
|-----|---------|-------------|
| morning_brief_time | 06:30 | Morning Brief delivery time (ET, 24hr) |
| eod_debrief_time | 23:00 | EOD Debrief delivery time (ET, 24hr) |
| social_listener_interval_hours | 4 | Hours between social listening runs |
| email_monitor_interval_hours | 1 | Hours between email monitor runs |

### Skill Toggles

| Key | Default | Description |
|-----|---------|-------------|
| morning_brief_enabled | true | Enable/disable morning brief |
| eod_debrief_enabled | true | Enable/disable EOD debrief |
| stale_radar_enabled | true | Enable/disable stale contact radar |
| fire_scan_enabled | true | Enable/disable fire scan |
| social_listener_enabled | false | Enable/disable social listener |
| email_monitor_enabled | false | Enable/disable email monitor |

### Thresholds

| Key | Default | Description |
|-----|---------|-------------|
| stale_contact_red_days | 7 | Days overdue → RED for high-importance contacts |
| stale_contact_yellow_days | 1 | Days overdue → YELLOW for high-importance contacts |
| stale_contact_med_red_days | 14 | Days overdue → RED for med-importance contacts |
| fire_scan_overdue_threshold | 0 | Days overdue for fire scan (0 = any) |

### Notification Preferences

| Key | Default | Description |
|-----|---------|-------------|
| notification_level | summary | Brief detail: `summary` or `detailed` |
| quiet_hours_start | 23:30 | No notifications after this time (ET) |
| quiet_hours_end | 06:00 | No notifications before this time (ET) |
| fire_scan_notify | true | Notify when fires detected |

### System

| Key | Default | Description |
|-----|---------|-------------|
| timezone | America/Detroit | Timezone for all calculations |
| ross_email | ross@trashpanda.capital | Primary email |

## How Workflow Skills Should Use Settings

Every scheduled/workflow skill should follow this pattern:

```python
# 1. Fetch all settings
settings = get_all_settings()  # using the curl pattern above

# 2. Check if enabled
if settings.get('morning_brief_enabled') != 'true':
    # Log as skipped, exit
    log_to_supabase(skill='morning-brief', status='skipped', summary='Disabled in settings')
    return

# 3. Check quiet hours before sending notifications
from datetime import datetime
import pytz
tz = pytz.timezone(settings.get('timezone', 'America/Detroit'))
now = datetime.now(tz)
quiet_start = settings.get('quiet_hours_start', '23:30')
quiet_end = settings.get('quiet_hours_end', '06:00')
# ... compare and skip notification if in quiet hours

# 4. Use thresholds
red_days = int(settings.get('stale_contact_red_days', '7'))
yellow_days = int(settings.get('stale_contact_yellow_days', '1'))
```

## Updating Settings

Ross edits settings directly in the Coda table. Skills can also update settings programmatically:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-ybi2tIogls/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{"cells": [
      {"column": "Key", "value": "morning_brief_time"},
      {"column": "Value", "value": "07:00"}
    ]}],
    "keyColumns": ["Key"]
  }'
```

## Adding New Settings

When building a new skill that needs config:
1. Add a row to the Settings table with the new Key
2. Document it in this skill's registry above
3. Have your skill read it at startup with a sensible default fallback

## Error Handling

- If the Settings table is unreachable, use hardcoded defaults (listed in the registry above)
- Never fail a skill run just because settings couldn't be read — fall back gracefully
- Log a warning if settings fetch fails so Ross knows config may be stale
