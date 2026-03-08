-- ============================================
-- Ross OS — Supabase History Tables Migration
-- Run in Supabase SQL Editor
-- ============================================

-- 1. Days History
CREATE TABLE IF NOT EXISTS days_history (
  id bigserial PRIMARY KEY,
  coda_row_id text UNIQUE,
  date date NOT NULL,
  start_of_day_intent text,
  end_of_day_summary text,
  sleep text,
  energy text,
  synced_at timestamptz DEFAULT now()
);

-- 2. Tasks History
CREATE TABLE IF NOT EXISTS tasks_history (
  id bigserial PRIMARY KEY,
  coda_row_id text UNIQUE,
  task text NOT NULL,
  context text,
  source text,
  status text,
  priority text,
  due_date date,
  assigned_day date,
  linked_contact text,
  created_at timestamptz,
  completed_at timestamptz,
  synced_at timestamptz DEFAULT now()
);

-- 3. Habits History
CREATE TABLE IF NOT EXISTS habits_history (
  id bigserial PRIMARY KEY,
  coda_row_id text UNIQUE,
  day date NOT NULL,
  habit_name text NOT NULL,
  count integer DEFAULT 0,
  completed boolean DEFAULT false,
  streak integer DEFAULT 0,
  synced_at timestamptz DEFAULT now()
);

-- 4. Workouts History
CREATE TABLE IF NOT EXISTS workouts_history (
  id bigserial PRIMARY KEY,
  coda_row_id text UNIQUE,
  day date NOT NULL,
  workout_name text,
  planned_start_time time,
  completed boolean DEFAULT false,
  weight_reps_distance text,
  duration text,
  notes text,
  synced_at timestamptz DEFAULT now()
);

-- 5. Contacts History
CREATE TABLE IF NOT EXISTS contacts_history (
  id bigserial PRIMARY KEY,
  coda_row_id text UNIQUE,
  name text NOT NULL,
  org text,
  role text,
  context_tags text,
  channels text,
  importance text,
  cadence integer,
  last_interaction_date date,
  next_touch_date date,
  synced_at timestamptz DEFAULT now()
);

-- 6. Interactions History
CREATE TABLE IF NOT EXISTS interactions_history (
  id bigserial PRIMARY KEY,
  coda_row_id text UNIQUE,
  contact_name text,
  date date,
  channel text,
  type text,
  notes text,
  related_day date,
  synced_at timestamptz DEFAULT now()
);

-- 7. Social Mentions History
CREATE TABLE IF NOT EXISTS social_mentions_history (
  id bigserial PRIMARY KEY,
  coda_row_id text UNIQUE,
  platform text,
  author_handle text,
  author_type text,
  date date,
  content text,
  link text,
  sentiment text,
  intent text,
  priority text,
  status text,
  synced_at timestamptz DEFAULT now()
);

-- 8. Market Intel History
CREATE TABLE IF NOT EXISTS market_intel_history (
  id bigserial PRIMARY KEY,
  coda_row_id text UNIQUE,
  source_platform text,
  entity_type text,
  person_name text,
  company_name text,
  signal_type text,
  signal_date date,
  raw_text_summary text,
  relevance text,
  priority text,
  status text,
  synced_at timestamptz DEFAULT now()
);

-- 9. Cleanup History
CREATE TABLE IF NOT EXISTS cleanup_history (
  id bigserial PRIMARY KEY,
  coda_row_id text UNIQUE,
  platform text,
  object_type text,
  identifier text,
  summary text,
  reason text,
  proposed_action text,
  status text,
  synced_at timestamptz DEFAULT now()
);

-- ============================================
-- Indexes for common query patterns
-- ============================================

CREATE INDEX IF NOT EXISTS idx_days_date ON days_history(date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks_history(status);
CREATE INDEX IF NOT EXISTS idx_tasks_context ON tasks_history(context);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks_history(due_date);
CREATE INDEX IF NOT EXISTS idx_habits_day ON habits_history(day);
CREATE INDEX IF NOT EXISTS idx_habits_name ON habits_history(habit_name);
CREATE INDEX IF NOT EXISTS idx_workouts_day ON workouts_history(day);
CREATE INDEX IF NOT EXISTS idx_contacts_importance ON contacts_history(importance);
CREATE INDEX IF NOT EXISTS idx_interactions_date ON interactions_history(date);
CREATE INDEX IF NOT EXISTS idx_interactions_contact ON interactions_history(contact_name);
CREATE INDEX IF NOT EXISTS idx_social_mentions_date ON social_mentions_history(date);
CREATE INDEX IF NOT EXISTS idx_social_mentions_status ON social_mentions_history(status);
CREATE INDEX IF NOT EXISTS idx_intel_signal_date ON market_intel_history(signal_date);
CREATE INDEX IF NOT EXISTS idx_intel_status ON market_intel_history(status);
CREATE INDEX IF NOT EXISTS idx_cleanup_status ON cleanup_history(status);

-- ============================================
-- Enable Row Level Security
-- ============================================

ALTER TABLE days_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE habits_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE workouts_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE interactions_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_mentions_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_intel_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE cleanup_history ENABLE ROW LEVEL SECURITY;

-- ============================================
-- Service role policies (full access via service key)
-- ============================================

CREATE POLICY "service_role_all" ON days_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON tasks_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON habits_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON workouts_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON contacts_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON interactions_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON social_mentions_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON market_intel_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON cleanup_history FOR ALL TO service_role USING (true) WITH CHECK (true);
