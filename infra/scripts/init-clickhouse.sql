-- ==============================================
-- Smart Mobility & Analytics Platform
-- ClickHouse Initialization Script
-- ==============================================
-- Star schema design for ride analytics.
-- Runs on first ClickHouse container start.
-- Engine selection:
--   MergeTree         — append-only facts (highest throughput)
--   ReplacingMergeTree — SCD Type 2 dimensions (dedup by version)
--   SummingMergeTree   — pre-aggregated rollups (auto-sum on merge)
--   AggregatingMergeTree — complex aggregate states (two-phase aggregation)

CREATE DATABASE IF NOT EXISTS mobility_analytics;

-- ══════════════════════════════════════════════
-- Dimension Tables
-- ══════════════════════════════════════════════

-- dim_time: Date/hour dimension for analytical joins
CREATE TABLE IF NOT EXISTS mobility_analytics.dim_time (
    date_key        UInt32,           -- YYYYMMDD
    full_date       Date,
    year            UInt16,
    quarter         UInt8,
    month           UInt8,
    month_name      LowCardinality(String),
    week            UInt8,
    day_of_month    UInt8,
    day_of_week     UInt8,
    day_name        LowCardinality(String),
    is_weekend      UInt8,
    is_holiday      UInt8
) ENGINE = MergeTree()
ORDER BY date_key;

-- dim_zones: NYC taxi zones (265 zones)
CREATE TABLE IF NOT EXISTS mobility_analytics.dim_zones (
    zone_id         UInt16,
    borough         LowCardinality(String),
    zone_name       String,
    service_zone    LowCardinality(String)
) ENGINE = ReplacingMergeTree()
ORDER BY zone_id;

-- dim_drivers: Slowly-changing dimension (Type 2)
CREATE TABLE IF NOT EXISTS mobility_analytics.dim_drivers (
    driver_key      UInt64,
    driver_id       String,
    full_name       String,
    license_number  String,
    rating          Float32,
    total_trips     UInt32,
    valid_from      DateTime,
    valid_to        DateTime DEFAULT '9999-12-31 23:59:59',
    is_current      UInt8 DEFAULT 1
) ENGINE = ReplacingMergeTree(valid_from)
ORDER BY (driver_id, valid_from);

-- dim_vehicles: Vehicle dimension
CREATE TABLE IF NOT EXISTS mobility_analytics.dim_vehicles (
    vehicle_key     UInt64,
    vehicle_id      String,
    make            String,
    model           String,
    year            UInt16,
    vehicle_type    LowCardinality(String),
    capacity        UInt8,
    valid_from      DateTime,
    valid_to        DateTime DEFAULT '9999-12-31 23:59:59',
    is_current      UInt8 DEFAULT 1
) ENGINE = ReplacingMergeTree(valid_from)
ORDER BY (vehicle_id, valid_from);

-- dim_weather: NOAA hourly weather observations
CREATE TABLE IF NOT EXISTS mobility_analytics.dim_weather (
    weather_key     UInt64,
    station_id      LowCardinality(String),
    observed_at     DateTime,
    temperature_f   Float32,
    humidity        Float32,
    wind_speed      Float32,
    precipitation   Float32,
    snow_depth      Float32,
    visibility      Float32,
    condition       LowCardinality(String)
) ENGINE = ReplacingMergeTree(observed_at)
ORDER BY (station_id, observed_at);

-- dim_payment_type: Small lookup
CREATE TABLE IF NOT EXISTS mobility_analytics.dim_payment_type (
    payment_type_id UInt8,
    payment_name    String
) ENGINE = MergeTree()
ORDER BY payment_type_id;

-- ══════════════════════════════════════════════
-- Fact Tables
-- ══════════════════════════════════════════════

-- fact_rides: Central fact table (target: 1.7B+ rows from NYC TLC data)
-- Partitioned by month for efficient time-range queries.
-- ORDER BY (pickup_zone_id, pickup_datetime) enables fast zone + time lookups.
CREATE TABLE IF NOT EXISTS mobility_analytics.fact_rides (
    ride_id                   String,
    vendor_id                 UInt8,
    pickup_datetime           DateTime,
    dropoff_datetime          DateTime,
    passenger_count           UInt8,
    trip_distance             Float32,
    pickup_zone_id            UInt16,
    dropoff_zone_id           UInt16,
    rate_code_id              UInt8,
    store_and_fwd             UInt8,
    payment_type_id           UInt8,
    fare_amount               Float32,
    extra                     Float32,
    mta_tax                   Float32,
    tip_amount                Float32,
    tolls_amount              Float32,
    improvement_surcharge     Float32,
    total_amount              Float32,
    congestion_surcharge      Float32,
    airport_fee               Float32,
    -- Derived columns (enriched during ETL)
    trip_duration_minutes     Float32,
    speed_mph                 Float32,
    pickup_hour               UInt8,
    pickup_day_of_week        UInt8,
    is_weekend                UInt8,
    -- Metadata
    source                    LowCardinality(String) DEFAULT 'nyc_tlc',
    ingested_at               DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(pickup_datetime)
ORDER BY (pickup_zone_id, pickup_datetime)
SETTINGS index_granularity = 8192;

-- fact_driver_locations: High-frequency GPS telemetry
-- 90-day TTL auto-deletes old location data.
CREATE TABLE IF NOT EXISTS mobility_analytics.fact_driver_locations (
    driver_id         String,
    latitude          Float64,
    longitude         Float64,
    heading           Float32,
    speed             Float32,
    accuracy          Float32,
    zone_id           UInt16,
    recorded_at       DateTime,
    ingested_at       DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(recorded_at)
ORDER BY (driver_id, recorded_at)
TTL recorded_at + INTERVAL 90 DAY;

-- fact_payments: Payment transactions
CREATE TABLE IF NOT EXISTS mobility_analytics.fact_payments (
    payment_id        String,
    trip_id           String,
    rider_id          String,
    driver_id         String,
    amount            Float32,
    currency          LowCardinality(String),
    payment_method    LowCardinality(String),
    status            LowCardinality(String),
    processed_at      DateTime,
    ingested_at       DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(processed_at)
ORDER BY (processed_at, trip_id);

-- fact_stream_metrics: Aggregated metrics from stream processors
CREATE TABLE IF NOT EXISTS mobility_analytics.fact_stream_metrics (
    metric_name       LowCardinality(String),
    metric_value      Float64,
    dimensions        Map(String, String),
    window_start      DateTime,
    window_end        DateTime,
    event_count       UInt64,
    ingested_at       DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(window_start)
ORDER BY (metric_name, window_start);

-- ══════════════════════════════════════════════
-- Materialized Views (Auto-Updated Aggregates)
-- ══════════════════════════════════════════════

-- Hourly ride aggregates per zone (SummingMergeTree auto-sums on merge)
CREATE MATERIALIZED VIEW IF NOT EXISTS mobility_analytics.mv_rides_hourly
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (pickup_zone_id, hour)
AS SELECT
    toStartOfHour(pickup_datetime)  AS hour,
    pickup_zone_id,
    count()                         AS ride_count,
    sum(total_amount)               AS total_revenue,
    sum(trip_distance)              AS total_distance,
    sum(tip_amount)                 AS total_tips,
    avg(trip_duration_minutes)      AS avg_duration,
    avg(trip_distance)              AS avg_distance,
    avg(total_amount)               AS avg_fare
FROM mobility_analytics.fact_rides
GROUP BY hour, pickup_zone_id;

-- Daily zone-to-zone flow aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS mobility_analytics.mv_rides_daily_zone
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(day)
ORDER BY (pickup_zone_id, dropoff_zone_id, day)
AS SELECT
    toDate(pickup_datetime)         AS day,
    pickup_zone_id,
    dropoff_zone_id,
    count()                         AS ride_count,
    sum(total_amount)               AS total_revenue,
    avg(trip_duration_minutes)      AS avg_duration,
    avg(speed_mph)                  AS avg_speed
FROM mobility_analytics.fact_rides
GROUP BY day, pickup_zone_id, dropoff_zone_id;

-- Driver performance (AggregatingMergeTree stores aggregate states)
CREATE MATERIALIZED VIEW IF NOT EXISTS mobility_analytics.mv_driver_performance
ENGINE = AggregatingMergeTree()
ORDER BY (driver_id, day)
AS SELECT
    driver_id,
    toDate(recorded_at)             AS day,
    countState()                    AS location_updates,
    avgState(speed)                 AS avg_speed,
    maxState(speed)                 AS max_speed
FROM mobility_analytics.fact_driver_locations
GROUP BY driver_id, day;

-- ══════════════════════════════════════════════
-- Data Quality Metrics Table
-- ══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mobility_analytics.data_quality_metrics (
    check_name        LowCardinality(String),
    table_name        LowCardinality(String),
    check_type        LowCardinality(String),
    status            LowCardinality(String),
    metric_value      Float64,
    threshold         Float64,
    details           String,
    checked_at        DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(checked_at)
ORDER BY (table_name, check_name, checked_at);

-- ══════════════════════════════════════════════
-- Skip Indexes (Query Optimization — M18)
-- ══════════════════════════════════════════════

ALTER TABLE mobility_analytics.fact_rides
    ADD INDEX IF NOT EXISTS idx_dropoff_zone dropoff_zone_id TYPE set(100) GRANULARITY 4;

ALTER TABLE mobility_analytics.fact_rides
    ADD INDEX IF NOT EXISTS idx_payment_type payment_type_id TYPE set(10) GRANULARITY 4;

ALTER TABLE mobility_analytics.fact_rides
    ADD INDEX IF NOT EXISTS idx_fare_range total_amount TYPE minmax GRANULARITY 4;

ALTER TABLE mobility_analytics.fact_rides
    ADD INDEX IF NOT EXISTS idx_distance_range trip_distance TYPE minmax GRANULARITY 4;

-- ══════════════════════════════════════════════
-- Seed Data
-- ══════════════════════════════════════════════

-- Payment type lookup
INSERT INTO mobility_analytics.dim_payment_type (payment_type_id, payment_name) VALUES
    (1, 'Credit Card'),
    (2, 'Cash'),
    (3, 'No Charge'),
    (4, 'Dispute'),
    (5, 'Unknown'),
    (6, 'Voided');

-- Populate dim_time for 2009-2026 (covers all NYC TLC data)
INSERT INTO mobility_analytics.dim_time
SELECT
    toUInt32(formatDateTime(d, '%Y%m%d'))    AS date_key,
    d                                        AS full_date,
    toYear(d)                                AS year,
    toQuarter(d)                             AS quarter,
    toMonth(d)                               AS month,
    formatDateTime(d, '%B')                  AS month_name,
    toISOWeek(d)                             AS week,
    toDayOfMonth(d)                          AS day_of_month,
    toDayOfWeek(d)                           AS day_of_week,
    formatDateTime(d, '%A')                  AS day_name,
    if(toDayOfWeek(d) >= 6, 1, 0)           AS is_weekend,
    0                                        AS is_holiday
FROM (
    SELECT toDate('2009-01-01') + number AS d
    FROM numbers(6575)   -- ~18 years of dates
);

-- ==============================================
-- Phase 4: ML Platform Tables
-- ==============================================

-- Feature values (offline feature store)
-- WHY ReplacingMergeTree: Features are recomputed periodically.
-- Deduplicates by computed_at on merge, keeping only the latest value.
CREATE TABLE IF NOT EXISTS mobility_analytics.ml_feature_values (
    entity_type     LowCardinality(String),
    entity_id       String,
    feature_name    LowCardinality(String),
    feature_value   Float64,
    computed_at     DateTime,
    ingested_at     DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(computed_at)
PARTITION BY toYYYYMM(computed_at)
ORDER BY (entity_type, entity_id, feature_name, computed_at);

-- Prediction log (append-only)
CREATE TABLE IF NOT EXISTS mobility_analytics.ml_prediction_log (
    prediction_id   String,
    model_name      LowCardinality(String),
    model_version   UInt32,
    features        String,                    -- JSON-encoded feature map
    prediction      Float64,
    confidence      Float32,
    latency_ms      Float32,
    request_source  LowCardinality(String),
    predicted_at    DateTime,
    ingested_at     DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(predicted_at)
ORDER BY (model_name, predicted_at);

-- Ground truth labels
CREATE TABLE IF NOT EXISTS mobility_analytics.ml_ground_truth (
    prediction_id   String,
    model_name      LowCardinality(String),
    actual_value    Float64,
    label_delay_s   UInt32,
    labeled_at      DateTime,
    ingested_at     DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(labeled_at)
ORDER BY (model_name, prediction_id);

-- Drift detection results
CREATE TABLE IF NOT EXISTS mobility_analytics.ml_drift_results (
    feature_name    LowCardinality(String),
    drift_type      LowCardinality(String),
    metric_name     LowCardinality(String),
    metric_value    Float64,
    threshold       Float64,
    is_drifted      UInt8,
    detected_at     DateTime,
    ingested_at     DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(detected_at)
ORDER BY (feature_name, detected_at);

-- Materialized view: prediction volume per model per hour
CREATE MATERIALIZED VIEW IF NOT EXISTS mobility_analytics.mv_prediction_volume_hourly
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (model_name, hour)
AS SELECT
    toStartOfHour(predicted_at)  AS hour,
    model_name,
    count()                      AS prediction_count,
    avg(latency_ms)              AS avg_latency_ms,
    avg(confidence)              AS avg_confidence
FROM mobility_analytics.ml_prediction_log
GROUP BY hour, model_name;
