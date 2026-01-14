# From Raw to Ready — End-to-End ML Data Pipeline

## What it does
- Ingests raw CSV into Postgres as immutable JSON events (aw.raw_events)
- Validates data and writes a validation report (rtifacts/reports/<run_id>.json)
- Cleans + dedupes into staging (stg.orders)
- Computes model-ready features via SQL (eats.customer_features)
- Creates time-aware train/val/test splits (meta.dataset_splits)
- Logs run metadata (meta.feature_registry)

## Quickstart (Windows)
### 1) Create venv + install deps
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

### 2) Start Postgres (Docker)
docker compose up -d

### 3) Run pipeline
python -m src.orchestrator.run --config configs/pipeline.yaml

## Inspect results
docker exec -it from-raw-to-ready-db-1 psql -U ml -d ml_pipeline
