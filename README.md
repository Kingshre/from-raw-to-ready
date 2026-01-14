# From Raw to Ready — End-to-End ML Data Pipeline

A production-style machine learning data pipeline that turns **messy raw data**
into **validated, versioned, model-ready features** using **Python, SQL, and Docker**.

This project demonstrates real-world ML/data engineering practices:
data quality gates, reproducibility, feature versioning, and time-aware splits.

---

## 🏗 Architecture

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
│ Dataset Splits │
│ meta.dataset_splits │
│ (train / val / test) │
└──────┬─────────────────┘
│
▼
┌────────────────────────┐
│ Feature Registry │
│ meta.feature_registry │
│ (versioning + lineage) │
└────────────────────────┘

markdown
Copy code

---

## 🔁 Data Flow (Step-by-Step)

1. **Ingest**
   - Reads raw CSV files
   - Stores each row as an immutable JSON record in Postgres
   - Table: `raw.raw_events`

2. **Validate**
   - Applies schema, null, range, and uniqueness checks
   - Rules defined in `configs/expectations.yaml`
   - Writes a machine-readable validation report
   - Fails fast if data quality issues are found

3. **Stage**
   - Cleans, deduplicates, and standardizes data
   - Output table: `stg.orders`

4. **Feature Engineering**
   - SQL-based rolling aggregations
   - Output table: `feats.customer_features`
   - Time-aware feature computation

5. **Splits & Registry**
   - Creates train / validation / test splits
   - Logs feature version, config hash, and SQL hash
   - Tables: `meta.dataset_splits`, `meta.feature_registry`

---

## 🧪 Validation Example

When data quality issues exist, the pipeline **stops automatically** and produces a report:

```json
{
  "validation_passed": false,
  "errors": [
    "order_id has 1 duplicate(s)",
    "amount has 1 < 0",
    "order_ts has 1 invalid timestamp(s)"
  ]
}
