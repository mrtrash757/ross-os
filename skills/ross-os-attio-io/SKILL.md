---
name: ross-os-attio-io
description: Read and write CRM data from Attio. Use this skill when you need to look up deals, companies, or people in the Attio CRM, sync contact data to Coda, or update deal stages. Currently disconnected — requires Ross to connect the Attio integration first.
metadata:
  author: ross-os
  version: '1.0'
  category: io
  status: stub
---

# Ross OS — Attio IO Skill

## When to Use This Skill

Load this skill when you need to:
- Look up company or contact details in the CRM
- Check deal pipeline status
- Sync Attio contacts with Coda's Contacts table
- Update deal stages or contact records
- Enrich Coda contact data with CRM fields

## Current Status: NOT YET CONNECTED

The Attio connector (`attio__pipedream`) is available but **disconnected**. Before using this skill:

1. Call `call_external_tool(tool_name="connect", source_id="attio__pipedream")` to get the OAuth URL
2. Have Ross authenticate with Attio
3. Then the tools below become available

## Expected Connector Tools

Once connected, these tools should be available via `source_id: "attio__pipedream"`:

- **List records** — Query people, companies, deals
- **Get record** — Fetch a specific record by ID
- **Create record** — Add new contacts, companies, or deals
- **Update record** — Modify existing records
- **Search** — Full-text search across the CRM

(Exact tool names and schemas will be available after connection.)

## Coda Integration

### Contacts Table (grid-1M2UOaliIC)

The Coda Contacts table is the system of record for Ross's network. Attio enriches it with:
- Company details (Org, Role)
- Deal context
- Communication history

**Sync pattern:** Pull from Attio → upsert into Coda Contacts using `keyColumns: ["Name"]`.

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Jane Smith"},
        {"column": "Org", "value": "Acme Corp"},
        {"column": "Role", "value": "CEO"},
        {"column": "Context tags", "value": "Investor"},
        {"column": "Channels", "value": "Email"},
        {"column": "Importance", "value": "High"},
        {"column": "Cadence", "value": 14}
      ]
    }],
    "keyColumns": ["Name"]
  }'
```

### Contacts Column Reference

| Column | Type |
|--------|------|
| Name | text |
| Org | text |
| Role | text |
| Notes | text |
| Context tags | select (Family / Operator / Investor / Ally / Threat / Other) |
| Channels | select (LI / X / Text / Email / In-person) |
| Importance | select (Low / Med / High) |
| Cadence | number (days between touches) |
| Last interaction date | date |
| LinkedIn URL | link |
| Next touch date | date |

## Planned Workflows

Once connected:

### Contact sync (Attio → Coda)
1. Fetch all contacts from Attio
2. For each, upsert into Coda Contacts table
3. Map Attio company → Coda Org, Attio role → Coda Role

### Deal pipeline check
1. Query Attio for active deals
2. Surface deals in Morning Brief with stage and next steps

### Contact enrichment
1. When a new contact is added to Coda, check Attio for additional data
2. Enrich with company info, deal context, LinkedIn URL

## Error Handling

- **Not connected:** Prompt Ross to authenticate the Attio connector.
- **API errors:** Follow standard retry pattern (wait 10s, max 3 retries).
- **Missing data:** Attio fields may be empty. Fall back to Coda data.

## TODO

- [ ] Connect Attio integration
- [ ] Map Attio fields to Coda columns
- [ ] Build contact sync recipe
- [ ] Build deal pipeline query
- [ ] Update this skill with actual tool names and schemas post-connection
