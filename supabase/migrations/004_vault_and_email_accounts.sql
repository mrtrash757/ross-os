-- Migration 004: Vault helper functions + email_accounts table
-- Run this in Supabase SQL Editor

-- ============================================================
-- 1. Vault helper functions (service_role only)
-- ============================================================

-- Insert a secret into Vault by name
CREATE OR REPLACE FUNCTION insert_secret(name text, secret text)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN vault.create_secret(secret, name);
END;
$$;

REVOKE EXECUTE ON FUNCTION insert_secret FROM public;
REVOKE EXECUTE ON FUNCTION insert_secret FROM anon;
REVOKE EXECUTE ON FUNCTION insert_secret FROM authenticated;
GRANT EXECUTE ON FUNCTION insert_secret TO service_role;

-- Read a secret from Vault by name
CREATE OR REPLACE FUNCTION read_secret(secret_name text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  secret text;
BEGIN
  SELECT decrypted_secret
  FROM vault.decrypted_secrets
  WHERE name = secret_name
  INTO secret;
  RETURN secret;
END;
$$;

REVOKE EXECUTE ON FUNCTION read_secret FROM public;
REVOKE EXECUTE ON FUNCTION read_secret FROM anon;
REVOKE EXECUTE ON FUNCTION read_secret FROM authenticated;
GRANT EXECUTE ON FUNCTION read_secret TO service_role;

-- Delete a secret from Vault by name
CREATE OR REPLACE FUNCTION delete_secret(secret_name text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  DELETE FROM vault.secrets WHERE name = secret_name;
END;
$$;

REVOKE EXECUTE ON FUNCTION delete_secret FROM public;
REVOKE EXECUTE ON FUNCTION delete_secret FROM anon;
REVOKE EXECUTE ON FUNCTION delete_secret FROM authenticated;
GRANT EXECUTE ON FUNCTION delete_secret TO service_role;

-- ============================================================
-- 2. Email accounts table (metadata only, no passwords)
-- ============================================================

CREATE TABLE IF NOT EXISTS email_accounts (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  account_name text UNIQUE NOT NULL,        -- e.g. 'personal', 'asteria', 'trashpanda'
  email_address text NOT NULL,              -- e.g. 'ross@asteriaair.com'
  account_type text NOT NULL DEFAULT 'workspace',  -- 'personal' or 'workspace'
  imap_server text NOT NULL DEFAULT 'imap.gmail.com',
  imap_port integer NOT NULL DEFAULT 993,
  smtp_server text NOT NULL DEFAULT 'smtp.gmail.com',
  smtp_port integer NOT NULL DEFAULT 587,
  vault_secret_name text NOT NULL,          -- references Vault secret, e.g. 'email_app_password_asteria'
  is_active boolean NOT NULL DEFAULT true,
  priority integer NOT NULL DEFAULT 5,      -- 1=highest priority inbox, 10=lowest
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- RLS: only service_role can access
ALTER TABLE email_accounts ENABLE ROW LEVEL SECURITY;

-- No policies = no access via anon/authenticated keys
-- Only service_role (which bypasses RLS) can read/write

COMMENT ON TABLE email_accounts IS 'Email account metadata for multi-inbox monitoring. Passwords stored in Vault, referenced by vault_secret_name.';
COMMENT ON COLUMN email_accounts.vault_secret_name IS 'Name of the Vault secret containing the app password. Use read_secret(vault_secret_name) to retrieve.';
COMMENT ON COLUMN email_accounts.priority IS '1 = highest priority inbox (checked first, alerts always). 10 = lowest priority (scanned, only alert on high-priority items).';
