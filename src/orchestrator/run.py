import argparse, yaml, subprocess, hashlib, json, os
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import text
from sqlalchemy import create_engine

def get_engine(db_url: str):
    return create_engine(db_url, future=True)

def git_sha():
    try:
        return subprocess.check_output(["git","rev-parse","HEAD"]).decode().strip()
    except Exception:
        return "unknown"

def file_hash(path: str) -> str:
    b = open(path, "rb").read()
    return hashlib.sha256(b).hexdigest()

def write_raw(engine, source_name: str, df: pd.DataFrame):
    sql = """
    INSERT INTO raw.raw_events (source, payload_json, payload_hash)
    VALUES (:source, CAST(:payload_json AS jsonb), :payload_hash)
    """
    with engine.begin() as conn:
        for r in df.to_dict(orient="records"):
            # Convert NaN / NaT to None so JSON is valid
            clean = {k: (None if pd.isna(v) else v) for k, v in r.items()}
            payload = json.dumps(clean, sort_keys=True, default=str, allow_nan=False)
            h = hashlib.sha256(payload.encode("utf-8")).hexdigest()

            conn.execute(
                text(sql),
                {
                    "source": source_name,
                    "payload_json": payload,
                    "payload_hash": h,
                },
            )



def validate_orders(df: pd.DataFrame, rules: dict):
    errs = []
    for c in rules["required_columns"]:
        if c not in df.columns:
            errs.append(f"Missing column: {c}")
    if errs:
        return False, errs

    for c in rules.get("non_null", []):
        n = df[c].isna().sum()
        if n > 0:
            errs.append(f"{c} has {n} null(s)")

    for c in rules.get("unique", []):
        d = df[c].duplicated().sum()
        if d > 0:
            errs.append(f"{c} has {d} duplicate(s)")

    df["order_ts"] = pd.to_datetime(df["order_ts"], errors="coerce", utc=True)
    bad_ts = df["order_ts"].isna().sum()
    if bad_ts > 0:
        errs.append(f"order_ts has {bad_ts} invalid timestamp(s)")

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    bad_amt = df["amount"].isna().sum()
    if bad_amt > 0:
        errs.append(f"amount has {bad_amt} non-numeric value(s)")

    r = rules.get("ranges", {}).get("amount")
    if r:
        low = (df["amount"] < r["min"]).sum()
        high = (df["amount"] > r["max"]).sum()
        if low > 0: errs.append(f"amount has {low} < {r['min']}")
        if high > 0: errs.append(f"amount has {high} > {r['max']}")

    allowed = set(rules.get("allowed_values", {}).get("status", []))
    df["status"] = df["status"].astype(str).str.replace("-", "", regex=False).str.lower()
    bad_status = (~df["status"].isin(allowed)).sum()
    if bad_status > 0:
        errs.append(f"status has {bad_status} invalid value(s)")

    return (len(errs) == 0), errs

def write_report(run_id: str, ok: bool, errors: list[str]):
    os.makedirs("artifacts/reports", exist_ok=True)
    path = f"artifacts/reports/{run_id}.json"
    with open(path, "w") as f:
        json.dump({"run_id": run_id, "validation_passed": ok, "errors": errors}, f, indent=2)
    return path

def write_stg_orders(engine, df: pd.DataFrame):
    df = df.dropna(subset=["order_id","customer_id","order_ts","amount"])
    df = df[df["amount"] >= 0]
    df = df.drop_duplicates(subset=["order_id"], keep="first")
    ins = """
    INSERT INTO stg.orders (order_id, customer_id, order_ts, amount, status)
    VALUES (:order_id, :customer_id, :order_ts, :amount, :status)
    ON CONFLICT (order_id) DO UPDATE SET
      customer_id=EXCLUDED.customer_id,
      order_ts=EXCLUDED.order_ts,
      amount=EXCLUDED.amount,
      status=EXCLUDED.status
    """
    with engine.begin() as conn:
        for r in df[["order_id","customer_id","order_ts","amount","status"]].to_dict(orient="records"):
            conn.execute(text(ins), r)

def compute_features(engine):
    sql = open("sql/marts.sql").read()
    with engine.begin() as conn:
        return conn.execute(text(sql)).mappings().all()

def write_features(engine, rows, feature_version: str):
    ins = """
    INSERT INTO feats.customer_features
      (customer_id, feature_time, orders_7d, orders_30d, revenue_30d, days_since_last_order, feature_version)
    VALUES
      (:customer_id, :feature_time, :orders_7d, :orders_30d, :revenue_30d, :days_since_last_order, :feature_version)
    ON CONFLICT (customer_id, feature_time, feature_version) DO NOTHING
    """
    with engine.begin() as conn:
        for r in rows:
            d = dict(r)
            d["feature_version"] = feature_version
            conn.execute(text(ins), d)

def write_registry(engine, feature_version: str, code_sha: str, source_hash: str, row_count: int, validation_passed: bool):
    ins = """
    INSERT INTO meta.feature_registry (feature_version, code_sha, source_hash, row_count, validation_passed)
    VALUES (:feature_version, :code_sha, :source_hash, :row_count, :validation_passed)
    ON CONFLICT (feature_version) DO NOTHING
    """
    with engine.begin() as conn:
        conn.execute(text(ins), {
            "feature_version": feature_version,
            "code_sha": code_sha,
            "source_hash": source_hash,
            "row_count": row_count,
            "validation_passed": validation_passed
        })

def create_time_splits(engine, feature_version: str, train=0.70, val=0.15):
    q = """
    SELECT customer_id, feature_time
    FROM feats.customer_features
    WHERE feature_version=:v
    ORDER BY feature_time
    """
    with engine.begin() as conn:
        rows = conn.execute(text(q), {"v": feature_version}).mappings().all()

    n = len(rows)
    train_end = int(n * train)
    val_end = int(n * (train + val))

    ins = """
    INSERT INTO meta.dataset_splits (customer_id, feature_time, split, feature_version)
    VALUES (:customer_id, :feature_time, :split, :feature_version)
    ON CONFLICT (customer_id, feature_time, feature_version) DO NOTHING
    """
    with engine.begin() as conn:
        for i, r in enumerate(rows):
            split = "train" if i < train_end else ("val" if i < val_end else "test")
            conn.execute(text(ins), {
                "customer_id": r["customer_id"],
                "feature_time": r["feature_time"],
                "split": split,
                "feature_version": feature_version
            })

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pipeline.yaml")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    
    engine = get_engine(cfg["db"]["url"])

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    feature_version = f"v{run_id}"

    src = cfg["sources"][0]
    df = pd.read_csv(src["path"])

    write_raw(engine, src["name"], df)

    rules = yaml.safe_load(open("configs/expectations.yaml"))["orders"]
    ok, errors = validate_orders(df.copy(), rules)
    report = write_report(run_id, ok, errors)
    print(f"Validation report: {report}")

    if cfg["validation"]["fail_on_error"] and not ok:
        raise SystemExit("Validation failed. Fix data or rules, then rerun.")

    df["order_ts"] = pd.to_datetime(df["order_ts"], errors="coerce", utc=True)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["status"] = df["status"].astype(str).str.replace("-", "", regex=False).str.lower()

    write_stg_orders(engine, df)

    rows = compute_features(engine)
    write_features(engine, rows, feature_version)
    write_registry(engine, feature_version, git_sha(), file_hash(src["path"]), len(rows), ok)
    create_time_splits(engine, feature_version,
                       cfg["splits"]["train_ratio"],
                       cfg["splits"]["val_ratio"])

    print(f"✅ Done. feature_version={feature_version}")

if __name__ == "__main__":
    main()
