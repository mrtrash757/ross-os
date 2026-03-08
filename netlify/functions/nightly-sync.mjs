// Nightly sync: Pull all rows from Coda tables, upsert into Supabase history tables
// Scheduled: 2am EST daily

const CODA_TOKEN = process.env.CODA_API_TOKEN;
const CODA_DOC = process.env.CODA_DOC_ID;
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

const CODA_BASE = `https://coda.io/apis/v1/docs/${CODA_DOC}`;

async function codaGet(endpoint) {
  const res = await fetch(`${CODA_BASE}/${endpoint}`, {
    headers: { Authorization: `Bearer ${CODA_TOKEN}` }
  });
  return res.json();
}

async function supabaseUpsert(table, rows) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: 'POST',
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      'Content-Type': 'application/json',
      Prefer: 'resolution=merge-duplicates'
    },
    body: JSON.stringify(rows)
  });
  return { status: res.status, ok: res.ok };
}

function extractCodaRows(items, columnMap) {
  return items.map(row => {
    const mapped = { coda_row_id: row.id };
    for (const [codaCol, supaCol] of Object.entries(columnMap)) {
      const val = row.values?.[codaCol];
      if (val !== undefined && val !== null && val !== '') {
        mapped[supaCol] = typeof val === 'object' ? JSON.stringify(val) : val;
      }
    }
    return mapped;
  });
}

async function syncTable(codaTableName, supaTable, columnMap) {
  try {
    // Get table ID
    const tables = await codaGet('tables');
    const table = tables.items?.find(t => t.name === codaTableName);
    if (!table) return { table: codaTableName, error: 'not found' };

    // Get rows
    const rows = await codaGet(`tables/${table.id}/rows?useColumnNames=true`);
    if (!rows.items?.length) return { table: codaTableName, rows: 0 };

    // Map and upsert
    const mapped = extractCodaRows(rows.items, columnMap);
    const result = await supabaseUpsert(supaTable, mapped);
    return { table: codaTableName, rows: mapped.length, supabase: result };
  } catch (err) {
    return { table: codaTableName, error: err.message };
  }
}

export default async (req) => {
  const results = [];

  // Days
  results.push(await syncTable('Days', 'days_history', {
    'Date': 'date',
    'Start of day intent': 'start_of_day_intent',
    'End of day summary': 'end_of_day_summary',
    'Sleep': 'sleep',
    'Energy': 'energy'
  }));

  // Habits (Habit Logs)
  results.push(await syncTable('Habit Logs', 'habits_history', {
    'Date': 'day',
    'Habit': 'habit_name',
    'Count': 'count',
    'Done?': 'completed'
  }));

  // Workout Instances
  results.push(await syncTable('Workout Instances', 'workouts_history', {
    'Date': 'day',
    'Workout': 'workout_name',
    'Planned start time': 'planned_start_time',
    'Completed?': 'completed',
    'Weight/reps/distance': 'weight_reps_distance',
    'Duration': 'duration',
    'Notes': 'notes'
  }));

  // Tasks
  results.push(await syncTable('Personal Asteria Tasks', 'tasks_history', {
    'Name': 'task',
    'Context': 'context',
    'Source': 'source',
    'Status': 'status',
    'Priority': 'priority',
    'Due date': 'due_date',
    'Created at': 'created_at',
    'Completed at': 'completed_at'
  }));

  // Contacts
  results.push(await syncTable('Contacts', 'contacts_history', {
    'Name': 'name',
    'Org': 'org',
    'Role': 'role',
    'Context tags': 'context_tags',
    'Channels': 'channels',
    'Importance': 'importance',
    'Cadence': 'cadence',
    'Last interaction date': 'last_interaction_date',
    'Next touch date': 'next_touch_date'
  }));

  // Interactions
  results.push(await syncTable('Interactions', 'interactions_history', {
    'Contact': 'contact_name',
    'Date': 'date',
    'Channel': 'channel',
    'Type': 'type',
    'Notes': 'notes'
  }));

  // Social Mentions
  results.push(await syncTable('Social Mentions Inbox', 'social_mentions_history', {
    'Platform': 'platform',
    'Author handle': 'author_handle',
    'Author type': 'author_type',
    'Date': 'date',
    'Content': 'content',
    'Link': 'link',
    'Sentiment': 'sentiment',
    'Intent': 'intent',
    'Priority': 'priority',
    'Status': 'status'
  }));

  // Market Intel
  results.push(await syncTable('Market Intel Events', 'market_intel_history', {
    'Source platform': 'source_platform',
    'Entity type': 'entity_type',
    'Person name': 'person_name',
    'Company name': 'company_name',
    'Signal type': 'signal_type',
    'Signal date': 'signal_date',
    'Raw text / summary': 'raw_text_summary',
    'Relevance': 'relevance',
    'Priority': 'priority',
    'Status': 'status'
  }));

  // Cleanup
  results.push(await syncTable('Network Cleanup Queue', 'cleanup_history', {
    'Platform': 'platform',
    'Object type': 'object_type',
    'Identifier': 'identifier',
    'Summary': 'summary',
    'Reason': 'reason',
    'Proposed action': 'proposed_action',
    'Status': 'status'
  }));

  return new Response(JSON.stringify({ synced_at: new Date().toISOString(), results }, null, 2), {
    headers: { 'Content-Type': 'application/json' }
  });
};

export const config = {
  schedule: "0 7 * * *"  // 7am UTC = 2am EST
};
