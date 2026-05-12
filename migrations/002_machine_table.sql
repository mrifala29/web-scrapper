-- ============================================================
-- ClickHouse Migration 002: Machine temperature table
-- Database: hbshengma
--
-- Run via SSH di server:
--   sudo docker exec -i clickhouse clickhouse-client \
--     --user LinkIT360 --password '@RnD123!' \
--     --multiquery < 002_machine_table.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS hbshengma.machine_temperature
(
    scrape_date        Date,
    scrape_timestamp   DateTime,
    machine_code       Nullable(String),
    machine_name       Nullable(String),
    temperature        Nullable(String),
    temperature_unit   Nullable(String),
    machine_status     Nullable(String),
    location           Nullable(String)
)
ENGINE = MergeTree()
PARTITION BY scrape_date
ORDER BY (scrape_date, scrape_timestamp)
SETTINGS index_granularity = 8192;
