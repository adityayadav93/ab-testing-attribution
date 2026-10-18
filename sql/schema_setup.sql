-- =============================================================================
-- schema_setup.sql  |  A/B testing & attribution warehouse
-- Dialect: ANSI / PostgreSQL (also runs unchanged on DuckDB, used for local runs)
-- =============================================================================

DROP TABLE IF EXISTS touchpoints;
DROP TABLE IF EXISTS journeys;
DROP TABLE IF EXISTS channel_spend;
DROP TABLE IF EXISTS experiment_users;

-- One row per user randomised into the checkout-redesign experiment ----------
CREATE TABLE experiment_users (
    user_id           VARCHAR(10) PRIMARY KEY,
    variant           VARCHAR(10) NOT NULL CHECK (variant IN ('control', 'treatment')),
    assigned_date     DATE        NOT NULL,
    device            VARCHAR(10) NOT NULL,
    is_returning      INTEGER     NOT NULL,          -- 1 = returning customer
    pre_period_spend  NUMERIC(10, 2) NOT NULL,       -- 30 days before assignment (CUPED covariate)
    converted         INTEGER     NOT NULL,          -- purchased during the test
    order_value       NUMERIC(10, 2) NOT NULL,       -- 0 if not converted
    refunded          INTEGER     NOT NULL           -- guardrail
);

-- One row per marketing journey -------------------------------------------------
CREATE TABLE journeys (
    journey_id     VARCHAR(10) PRIMARY KEY,
    user_id        VARCHAR(10) NOT NULL,
    converted      INTEGER     NOT NULL,
    conversion_ts  TIMESTAMP,
    revenue        NUMERIC(10, 2) NOT NULL
);

-- One row per touch; touch_order 1 = first touch -------------------------------
CREATE TABLE touchpoints (
    journey_id   VARCHAR(10) NOT NULL REFERENCES journeys (journey_id),
    touch_order  INTEGER     NOT NULL,
    channel      VARCHAR(20) NOT NULL,
    touch_ts     TIMESTAMP   NOT NULL,
    PRIMARY KEY (journey_id, touch_order)
);

-- Quarterly spend by channel ---------------------------------------------------
CREATE TABLE channel_spend (
    channel  VARCHAR(20) PRIMARY KEY,
    spend    NUMERIC(12, 2) NOT NULL
);

CREATE INDEX idx_touch_journey ON touchpoints (journey_id);
