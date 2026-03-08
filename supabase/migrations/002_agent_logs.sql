-- Agent Logs table for tracking all skill executions
-- Part of Ross OS orchestrator logging framework

CREATE TABLE IF NOT EXISTS agent_logs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  skill_name text NOT NULL,
  triggered_by text NOT NULL DEFAULT 'manual',  -- manual / schedule / skill:{name}
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  status text NOT NULL DEFAULT 'running',  -- running / success / error / partial
  summary text,
  detail jsonb,
  error text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_agent_logs_skill ON agent_logs(skill_name);
CREATE INDEX idx_agent_logs_status ON agent_logs(status);
CREATE INDEX idx_agent_logs_started ON agent_logs(started_at DESC);

-- RLS: service role only (same pattern as history tables)
ALTER TABLE agent_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on agent_logs"
  ON agent_logs
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
