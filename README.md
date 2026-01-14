# From Raw to Ready — End-to-End ML Data Pipeline

A production-style machine learning data pipeline that transforms **messy raw data**
into **validated, versioned, model-ready features** using **Python, SQL, PostgreSQL, and Docker**.

This project focuses on the parts of ML systems that matter most in real-world production:
data quality enforcement, reproducibility, feature engineering, and time-aware dataset preparation.

---

## 🏗 Architecture Overview

┌──────────────┐
│ Raw CSV Data │
│ (data/raw) │
└──────┬───────┘
│
▼
┌────────────────────────┐
│ Ingestion │
│ raw.raw_events │
│ (immutable JSON events) │
└──────┬─────────────────┘
│
▼
┌────────────────────────┐
│ Validation │
│ configs/expectations │
│ → artifacts/reports │
└──────┬─────────────────┘
│
▼
┌────────────────────────┐
│ Staging │
│ stg.orders │
│ (clean + deduplicated) │
└──────┬─────────────────┘
│
▼
┌────────────────────────┐
│ Feature Engineering │
│ sql/marts.sql │
│ feats.customer_features │
└──────┬─────────────────┘
│
▼
┌────────────────────────┐
│ Splits & Registry │
│ meta.dataset_splits │
│ meta.feature_registry │
└────────────────────────┘

yaml
Copy code

---

## 🔁 Data Flow (Step-by-Step)

### 1. Ingestion
Raw CSV files are read and each row is stored as an immutable JSON record in PostgreSQL.
This preserves the original data exactly as received and enables replayability.

**Table:** `raw.raw_events`

---

### 2. Validation
Data quality rules are applied before any downstream processing:
- Schema checks
- Null checks
- Range checks
- Uniqueness constraints

Rules are defined in `configs/expectations.yaml`.

If validation fails, the pipeline **stops immediately** and writes a machine-readable
validation report to `artifacts/reports/<run_id>.json`.

---

### 3. Staging
Validated data is cleaned, standardized, and deduplicated before being written
to the staging layer.

**Table:** `stg.orders`

---

### 4. Feature Engineering
SQL-based feature engineering computes rolling aggregations and behavioral features
in a time-aware manner.

Feature logic is defined in `sql/marts.sql`.

**Table:** `feats.customer_features`

---

### 5. Splits & Feature Registry
The pipeline creates time-aware train, validation, and test splits and records
metadata about the run, including configuration hashes and SQL hashes.

**Tables:**
- `meta.dataset_splits`
- `meta.feature_registry`

---

## 🧪 Validation Example

When data quality issues exist, the pipeline fails fast and produces a detailed report:

```json
{
  "validation_passed": false,
  "errors": [
    "order_id has duplicate values",
    "amount has negative values",
    "order_ts has invalid timestamps"
  ]
}
This enforces production-grade data quality gates.

📊 Feature Example
Example rows from feats.customer_features:

customer_id	feature_time	orders_7d	orders_30d	revenue_30d	days_since_last_order
C001	2025-12-05	2	2	49.98	4
C002	2025-12-15	1	2	117.50	5

These features are model-ready and can be used directly for training.

🚀 How to Run Locally
Prerequisites
Python 3.10+

Docker + Docker Compose

Git

1. Create a virtual environment
bash
Copy code
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
2. Start PostgreSQL
bash
Copy code
docker compose up -d
3. Run the pipeline
bash
Copy code
python -m src.orchestrator.run --config configs/pipeline.yaml
🔍 Inspect Results
bash
Copy code
docker exec -it from-raw-to-ready-db-1 psql -U ml -d ml_pipeline
sql
Copy code
SELECT * FROM stg.orders;
SELECT * FROM feats.customer_features;
SELECT split, COUNT(*) FROM meta.dataset_splits GROUP BY split;
🧠 Why This Project Matters
This project demonstrates:

Immutable raw data ingestion

Strict data quality enforcement

SQL-based feature engineering

Feature versioning and lineage

Time-aware ML dataset preparation

Reproducible end-to-end pipelines

This mirrors real ML/data engineering systems used in production — not toy notebooks.

🛠 Tech Stack
Python (pandas, SQLAlchemy)

PostgreSQL

SQL (feature engineering)

Docker / Docker Compose

YAML-based configuration

📌 Future Improvements
Add model training and evaluation

Add CI (GitHub Actions)

Add cloud storage (S3-style)

Add automated data tests and alerts
