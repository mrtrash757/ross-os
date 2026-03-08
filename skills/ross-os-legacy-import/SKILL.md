---
name: ross-os-legacy-import
description: One-time Hivekiln data import helper. Use this skill to map and import Ross's historical data from Hivekiln exports into Ross OS Coda tables — Workouts, Workout Instances, Habits, Habit Logs, and Days. Handles data mapping, deduplication, and validation.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io
---

# Ross OS — Legacy Import Helper (Hivekiln)

## When to Use This Skill

Load this skill when:
- Ross wants to import historical data from Hivekiln
- Ross provides Hivekiln export files (CSV, JSON, or other format)
- Setting up Ross OS for the first time and backfilling historical data

## Overview

Hivekiln was Ross's previous tracking system. This skill maps Hivekiln data structures to Ross OS Coda tables. It's designed as a one-time import, not an ongoing sync.

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Hivekiln Import Staging Table:** `grid-TAFYZLAB9W`

**Target Tables:**
- **Workouts:** `grid-kOoUMffFTS`
- **Workout Instances:** `grid-vEv0-YZI9h`
- **Habits:** `grid-5WHcBsnbmk`
- **Habit Logs:** `grid-5FJBmY91ko`
- **Days:** `grid-Zm8ylxf9zc`

## Instructions

### Step 1: Get Hivekiln Export

Ask Ross to provide the Hivekiln export. Common formats:
- CSV export (one file per entity type)
- JSON export
- Database dump

If Ross doesn't have the export yet, help him locate and download it from Hivekiln.

### Step 2: Load into Staging Table

First, load the raw data into the Hivekiln Import Staging table for review:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-TAFYZLAB9W/columns" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Check what columns exist. Write raw imported data there first for Ross to review before mapping.

### Step 3: Map Fields

Create a mapping between Hivekiln fields and Ross OS fields. This depends on the actual Hivekiln export structure. Common mappings:

#### Workouts (exercise templates)
| Hivekiln Field | Ross OS Field | Table |
|---------------|---------------|-------|
| Exercise name | Name | Workouts (grid-kOoUMffFTS) |
| Category | Type | Workouts |
| Description | Notes | Workouts |

#### Workout Instances (actual sessions)
| Hivekiln Field | Ross OS Field | Table |
|---------------|---------------|-------|
| Date | Date | Workout Instances (grid-vEv0-YZI9h) |
| Exercise | Workout | Workout Instances |
| Sets / Reps / Weight | Details | Workout Instances |
| Duration | Duration | Workout Instances |
| Notes | Notes | Workout Instances |

#### Habits (habit definitions)
| Hivekiln Field | Ross OS Field | Table |
|---------------|---------------|-------|
| Habit name | Name | Habits (grid-5WHcBsnbmk) |
| Frequency | Frequency | Habits |
| Category | Category | Habits |

#### Habit Logs (daily tracking)
| Hivekiln Field | Ross OS Field | Table |
|---------------|---------------|-------|
| Date | Date | Habit Logs (grid-5FJBmY91ko) |
| Habit | Habit | Habit Logs |
| Completed | Status | Habit Logs |
| Notes | Notes | Habit Logs |

#### Days (daily journal)
| Hivekiln Field | Ross OS Field | Table |
|---------------|---------------|-------|
| Date | Date | Days (grid-Zm8ylxf9zc) |
| Notes / Journal | Notes | Days |
| Mood / Energy | Mood | Days |

### Step 4: Transform Data

Write a Python script to transform Hivekiln data into Coda-compatible format:

```python
import json, csv

# Read Hivekiln export
with open('/home/user/workspace/hivekiln_export.csv') as f:
    reader = csv.DictReader(f)
    hk_data = list(reader)

# Transform to Coda rows
coda_rows = []
for row in hk_data:
    coda_rows.append({
        "cells": [
            {"column": "Name", "value": row["exercise_name"]},
            {"column": "Date", "value": row["date"]},
            # ... map all fields
        ]
    })

# Write to file for batch import
with open('/home/user/workspace/coda_import.json', 'w') as f:
    json.dump({"rows": coda_rows}, f)
```

### Step 5: Validate Before Import

Before writing to Coda:
1. Check for duplicates (same date + same entity in target table)
2. Validate date formats (ISO 8601)
3. Validate references (e.g., Workout Instance references a Workout that exists)
4. Count rows per table and confirm with Ross

Present validation report:
```
## Import Validation

Ready to import:
- 12 Workout templates
- 340 Workout instances (Jan 2024 - Feb 2026)
- 8 Habit definitions
- 1,200 Habit log entries
- 400 Day entries

Issues found:
- 3 workout instances reference unknown exercises (will create new)
- 15 habit logs have missing dates (will skip)

Proceed with import?
```

### Step 6: Import to Coda

Batch import in chunks of 50 rows (Coda limit consideration):

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/{TABLE_ID}/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @/home/user/workspace/coda_import_batch_1.json
```

Add 2-second delays between batches to respect rate limits.

### Step 7: Verify Import

After import, count rows in each target table and compare:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/{TABLE_ID}/rows?useColumnNames=true&limit=1" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Check the response headers for total row count. Report:
```
## Import Complete

- Workouts: 12 imported (12 expected) ✓
- Workout Instances: 337 imported (340 expected) — 3 skipped (invalid dates)
- Habits: 8 imported (8 expected) ✓
- Habit Logs: 1,185 imported (1,200 expected) — 15 skipped (missing dates)
- Days: 400 imported (400 expected) ✓
```

## Error Handling

- Export format unknown → Ask Ross for details, inspect file structure
- Duplicate data → Skip duplicates, report count
- Rate limit hit → Pause 10 seconds, retry, reduce batch size if needed
- Missing required fields → Skip row, log to report
- Table column mismatch → Check actual columns first, adapt mapping
- Large dataset (1000+ rows) → Process in batches with progress reporting

## Notes

- This is a one-time import skill — run once, verify, done
- Keep the staging table data for reference even after import
- If Ross needs to re-import, clear target table first (or use keyColumns for upsert)
- Hivekiln export format may vary — adapt the mapping based on actual file structure
