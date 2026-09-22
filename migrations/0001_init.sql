-- content-agent — schema inicial (migration 0001)
-- Banco de DOMÍNIO do projeto (separado do state.db nativo do Hermes).
-- SQLite. Chaves estrangeiras ON; índices em status/timestamps; transações para reserva de cota.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS niches (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  audience_score REAL,
  commercial_score REAL,
  feasibility_score REAL,
  confidence_score REAL,
  status TEXT NOT NULL DEFAULT 'rascunho',
  evidence_summary TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  platform TEXT,
  creator TEXT,
  published_at TEXT,
  collected_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  language TEXT,
  metrics_json TEXT,
  summary TEXT,
  limitations TEXT,
  content_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_sources_platform ON sources(platform);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_hash ON sources(content_hash);

CREATE TABLE IF NOT EXISTS ideas (
  id TEXT PRIMARY KEY,
  niche_id TEXT REFERENCES niches(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  audience TEXT,
  objective TEXT,
  hypothesis TEXT,
  base_script TEXT,
  scene_plan_json TEXT,
  status TEXT NOT NULL DEFAULT 'rascunho',
  priority INTEGER DEFAULT 0,
  estimated_cost REAL DEFAULT 0,
  actual_cost REAL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);

CREATE TABLE IF NOT EXISTS idea_sources (
  idea_id TEXT NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  usage_note TEXT,
  PRIMARY KEY (idea_id, source_id)
);

CREATE TABLE IF NOT EXISTS language_variants (
  id TEXT PRIMARY KEY,
  idea_id TEXT NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
  locale TEXT NOT NULL,               -- pt-BR | en | es
  script TEXT,
  onscreen_text_json TEXT,
  caption_path TEXT,
  voice_path TEXT,
  video_path TEXT,
  thumbnail_path TEXT,
  metadata_json TEXT,
  status TEXT NOT NULL DEFAULT 'aguardando',
  revision_count INTEGER NOT NULL DEFAULT 0,
  review_json TEXT,
  UNIQUE (idea_id, locale)
);
CREATE INDEX IF NOT EXISTS idx_variants_status ON language_variants(status);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  idea_id TEXT REFERENCES ideas(id) ON DELETE CASCADE,
  variant_id TEXT REFERENCES language_variants(id) ON DELETE CASCADE,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pendente',
  attempt INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3,
  provider TEXT,
  external_job_id TEXT,
  input_hash TEXT,                    -- idempotência: mesma entrada => não repetir
  started_at TEXT,
  finished_at TEXT,
  error_code TEXT,
  error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_input_hash ON jobs(input_hash);

CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  idea_id TEXT REFERENCES ideas(id) ON DELETE CASCADE,
  variant_id TEXT REFERENCES language_variants(id) ON DELETE CASCADE,
  artifact_type TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT,
  size_bytes INTEGER,
  metadata_json TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS provider_accounts (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,             -- flow | openrouter | nvidia | qwen | ...
  label TEXT,
  plan TEXT,
  quota_total REAL,
  quota_remaining_observed REAL,
  quota_reserved REAL DEFAULT 0,
  renews_at TEXT,
  status TEXT NOT NULL DEFAULT 'ativo',
  last_checked_at TEXT
  -- NUNCA armazenar segredos/cookies aqui.
);

CREATE TABLE IF NOT EXISTS usage_events (
  id TEXT PRIMARY KEY,
  provider_account_id TEXT REFERENCES provider_accounts(id) ON DELETE SET NULL,
  job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
  unit TEXT,                          -- credito | token | requisicao | brl
  estimated_amount REAL,
  actual_amount REAL,
  currency TEXT,
  occurred_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  metadata_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_usage_occurred ON usage_events(occurred_at);

CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT,
  event_type TEXT NOT NULL,
  actor TEXT,
  details_json TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at);

-- controle de versão de schema
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
INSERT OR IGNORE INTO schema_migrations(version) VALUES (1);
