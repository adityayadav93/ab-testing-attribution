-- =============================================================================
-- attribution_queries.sql  |  Rule-based attribution models in pure SQL
-- Converted journeys only. Window functions: ROW_NUMBER, COUNT, MAX over journey.
-- Data-driven (Markov) attribution is in notebooks/02_attribution_modeling.ipynb.
-- Dialect: PostgreSQL-compatible.
-- =============================================================================


-- name: attr_path_stats
-- Journey length distribution by outcome.
SELECT
    j.converted,
    COUNT(*)                         AS journeys,
    ROUND(AVG(n.touches), 2)         AS avg_touches,
    MAX(n.touches)                   AS max_touches
FROM journeys j
JOIN (SELECT journey_id, COUNT(*) AS touches FROM touchpoints GROUP BY journey_id) n USING (journey_id)
GROUP BY j.converted
ORDER BY j.converted;


-- name: attr_rule_based
-- Credit (conversions and revenue) per channel under five rule-based models.
WITH conv_touches AS (
    SELECT
        t.journey_id,
        t.channel,
        t.touch_order,
        t.touch_ts,
        j.revenue,
        j.conversion_ts,
        COUNT(*)      OVER (PARTITION BY t.journey_id)                            AS n_touches,
        -- days between the touch and the conversion
        EXTRACT(EPOCH FROM (j.conversion_ts - t.touch_ts)) / 86400.0               AS days_before_conv
    FROM touchpoints t
    JOIN journeys j USING (journey_id)
    WHERE j.converted = 1
),
weighted AS (
    SELECT
        *,
        CASE WHEN touch_order = 1          THEN 1.0 ELSE 0.0 END                  AS w_first,
        CASE WHEN touch_order = n_touches  THEN 1.0 ELSE 0.0 END                  AS w_last,
        1.0 / n_touches                                                           AS w_linear,
        -- position based (U-shaped): 40% first, 40% last, 20% spread over the middle
        CASE
            WHEN n_touches = 1 THEN 1.0
            WHEN n_touches = 2 THEN 0.5
            WHEN touch_order = 1 OR touch_order = n_touches THEN 0.4
            ELSE 0.2 / (n_touches - 2)
        END                                                                       AS w_position,
        -- time decay: half-life of 7 days, normalised within the journey
        POWER(0.5, days_before_conv / 7.0)                                        AS decay_raw
    FROM conv_touches
),
normalised AS (
    SELECT *, decay_raw / SUM(decay_raw) OVER (PARTITION BY journey_id) AS w_decay
    FROM weighted
)
SELECT
    channel,
    ROUND(SUM(w_first), 1)                  AS first_touch_conv,
    ROUND(SUM(w_last), 1)                   AS last_touch_conv,
    ROUND(SUM(w_linear), 1)                 AS linear_conv,
    ROUND(SUM(w_position), 1)               AS position_conv,
    ROUND(SUM(w_decay), 1)                  AS time_decay_conv,
    ROUND(SUM(w_first    * revenue), 0)     AS first_touch_rev,
    ROUND(SUM(w_last     * revenue), 0)     AS last_touch_rev,
    ROUND(SUM(w_linear   * revenue), 0)     AS linear_rev,
    ROUND(SUM(w_position * revenue), 0)     AS position_rev,
    ROUND(SUM(w_decay    * revenue), 0)     AS time_decay_rev
FROM normalised
GROUP BY channel
ORDER BY channel;


-- name: attr_assist_ratio
-- How often each channel appears as an assist (in the journey, not the last touch) vs closer.
WITH conv AS (
    SELECT t.journey_id, t.channel, t.touch_order,
           MAX(t.touch_order) OVER (PARTITION BY t.journey_id) AS last_order
    FROM touchpoints t
    JOIN journeys j USING (journey_id)
    WHERE j.converted = 1
)
SELECT
    channel,
    SUM(CASE WHEN touch_order <  last_order THEN 1 ELSE 0 END) AS assists,
    SUM(CASE WHEN touch_order =  last_order THEN 1 ELSE 0 END) AS closes,
    ROUND(1.0 * SUM(CASE WHEN touch_order < last_order THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN touch_order = last_order THEN 1 ELSE 0 END), 0), 2) AS assist_to_close_ratio
FROM conv
GROUP BY channel
ORDER BY assist_to_close_ratio DESC;


-- name: attr_paths
-- Full ordered path per journey (input for the Markov model).
SELECT
    j.journey_id,
    j.converted,
    j.revenue,
    STRING_AGG(t.channel, ' > ' ORDER BY t.touch_order) AS path
FROM journeys j
JOIN touchpoints t USING (journey_id)
GROUP BY j.journey_id, j.converted, j.revenue
ORDER BY j.journey_id;
