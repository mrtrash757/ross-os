-- Agent Actions table for granular action-level logging
-- Linked to agent_logs for parent skill execution context
-- Part of Ross OS Enhanced Logging (#18)

CREATE TABLE IF NOT EXISTS agent_actions (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  log_id uuid REFERENCES agent_logs(id) ON DELETE CASCADE,
  action_name text NOT NULL,
  action_type text NOT NULL DEFAULT 'api_call',  -- api_call / data_read / data_write / classify / notify / compute
  target_system text,  -- coda / supabase / gmail / gcal / x / linkedin / todoist
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  status text NOT NULL DEFAULT 'running',  -- running / success / error / skipped
  input_summary text,  -- brief description of what was sent
  output_summary text,  -- brief description of what came back
  row_count integer,  -- number of rows read/written if applicable
  duration_ms integer,  -- computed on completion
  error text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_agent_actions_log ON agent_actions(log_id);
CREATE INDEX idx_agent_actions_type ON agent_actions(action_type);
CREATE INDEX idx_agent_actions_status ON agent_actions(status);

-- RLS: service role only
ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on agent_actions"
  ON agent_actions
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Performance analytics RPC function
CREATE OR REPLACE FUNCTION skill_performance(days_back integer DEFAULT 7)
RETURNS TABLE(
  skill_name text,
  total_runs bigint,
  success_count bigint,
  error_count bigint,
  avg_duration_seconds numeric,
  last_run timestamptz
) AS $$
  SELECT
    l.skill_name,
    count(*) as total_runs,
    count(*) FILTER (WHERE l.status = 'success') as success_count,
    count(*) FILTER (WHERE l.status = 'error') as error_count,
    round(avg(EXTRACT(EPOCH FROM (l.completed_at - l.started_at)))::numeric, 1) as avg_duration_seconds,
    max(l.started_at) as last_run
  FROM agent_logs l
  WHERE l.started_at >= now() - (days_back || ' days')::interval
  GROUP BY l.skill_name
  ORDER BY total_runs DESC;
$$ LANGUAGE sql STABLE;
