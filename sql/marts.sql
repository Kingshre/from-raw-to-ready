WITH base AS (
  SELECT
    o.customer_id,
    o.order_ts AS feature_time
  FROM stg.orders o
),
agg AS (
  SELECT
    b.customer_id,
    b.feature_time,
    COUNT(*) FILTER (WHERE o.order_ts >= b.feature_time - interval '7 days' AND o.order_ts <= b.feature_time) AS orders_7d,
    COUNT(*) FILTER (WHERE o.order_ts >= b.feature_time - interval '30 days' AND o.order_ts <= b.feature_time) AS orders_30d,
    COALESCE(SUM(o.amount) FILTER (WHERE o.order_ts >= b.feature_time - interval '30 days' AND o.order_ts <= b.feature_time), 0) AS revenue_30d,
    COALESCE(EXTRACT(day FROM (b.feature_time - MAX(o.order_ts) FILTER (WHERE o.order_ts < b.feature_time))), 9999)::int AS days_since_last_order
  FROM base b
  JOIN stg.orders o
    ON o.customer_id = b.customer_id
   AND o.order_ts <= b.feature_time
  GROUP BY 1,2
)
SELECT * FROM agg;
