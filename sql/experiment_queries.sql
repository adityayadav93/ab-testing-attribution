-- =============================================================================
-- experiment_queries.sql  |  A/B test data checks and descriptive aggregates
-- Tagged `-- name: <id>`; src/build_warehouse.py writes data/processed/<id>.csv.
-- Statistical tests live in notebooks/01_ab_test_analysis.ipynb.
-- =============================================================================


-- name: exp_arm_counts
-- Sample-ratio-mismatch (SRM) input: users per arm.
SELECT variant, COUNT(*) AS users
FROM experiment_users
GROUP BY variant
ORDER BY variant;


-- name: exp_summary_by_variant
-- Primary, secondary and guardrail metrics per arm.
SELECT
    variant,
    COUNT(*)                                               AS users,
    SUM(converted)                                         AS orders,
    ROUND(100.0 * SUM(converted) / COUNT(*), 3)            AS conversion_pct,
    ROUND(SUM(order_value) / COUNT(*), 4)                  AS revenue_per_visitor,
    ROUND(SUM(order_value) / NULLIF(SUM(converted), 0), 2) AS avg_order_value,
    ROUND(100.0 * SUM(refunded) / NULLIF(SUM(converted), 0), 3) AS refund_pct_of_orders
FROM experiment_users
GROUP BY variant
ORDER BY variant;


-- name: exp_summary_by_segment
-- Same metrics by device and customer type (heterogeneity input).
WITH seg AS (
    SELECT 'device' AS dimension, device AS segment, variant, converted, order_value FROM experiment_users
    UNION ALL
    SELECT 'customer_type', CASE WHEN is_returning = 1 THEN 'returning' ELSE 'new' END, variant, converted, order_value
    FROM experiment_users
)
SELECT
    dimension, segment, variant,
    COUNT(*)                                    AS users,
    SUM(converted)                              AS orders,
    ROUND(100.0 * SUM(converted) / COUNT(*), 3) AS conversion_pct,
    ROUND(SUM(order_value) / COUNT(*), 4)       AS revenue_per_visitor
FROM seg
GROUP BY dimension, segment, variant
ORDER BY dimension, segment, variant;


-- name: exp_daily
-- Daily and cumulative conversion by arm. Window functions: running SUMs.
WITH daily AS (
    SELECT assigned_date, variant, COUNT(*) AS users, SUM(converted) AS orders
    FROM experiment_users
    GROUP BY assigned_date, variant
)
SELECT
    assigned_date,
    variant,
    users,
    orders,
    ROUND(100.0 * orders / users, 3) AS daily_conversion_pct,
    SUM(users)  OVER (PARTITION BY variant ORDER BY assigned_date) AS cum_users,
    SUM(orders) OVER (PARTITION BY variant ORDER BY assigned_date) AS cum_orders
FROM daily
ORDER BY assigned_date, variant;


-- name: exp_users
-- User-level table used for the statistical tests.
SELECT * FROM experiment_users ORDER BY user_id;
