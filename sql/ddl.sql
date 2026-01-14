CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS feats;
CREATE SCHEMA IF NOT EXISTS meta;

CREATE TABLE IF NOT EXISTS raw.raw_events (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload_json JSONB NOT NULL,
  payload_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stg.orders (
  order_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  order_ts TIMESTAMPTZ NOT NULL,
  amount NUMERIC NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feats.customer_features (
  customer_id TEXT NOT NULL,
  feature_time TIMESTAMPTZ NOT NULL,
  orders_7d INT NOT NULL,
  orders_30d INT NOT NULL,
  revenue_30d NUMERIC NOT NULL,
  days_since_last_order INT NOT NULL,
  feature_version TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (customer_id, feature_time, feature_version)
);

CREATE TABLE IF NOT EXISTS meta.feature_registry (
  feature_version TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  code_sha TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  row_count BIGINT NOT NULL,
  validation_passed BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS meta.dataset_splits (
  customer_id TEXT NOT NULL,
  feature_time TIMESTAMPTZ NOT NULL,
  split TEXT NOT NULL CHECK (split IN ('train','val','test')),
  feature_version TEXT NOT NULL,
  PRIMARY KEY (customer_id, feature_time, feature_version)
);
