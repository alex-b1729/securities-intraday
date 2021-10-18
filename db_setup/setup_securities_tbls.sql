-- setup tables within securities database

-- extend with timescaledb
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Table to track info for each security
CREATE TABLE IF NOT EXISTS "security_info" (
    security_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, -- unique id to use across database
    symbol JSONB NOT NULL, -- symbol as reported by IEX API & previous depreciated symbols
    exchange TEXT,
    comp_name TEXT,
    date_added DATE, -- date added to table
    date_depreciated DATE,  -- date no longer supported by IEX API, can be null
    security_type TEXT,
    iex_id TEXT,
    region TEXT,
    currency TEXT,
    is_enabled BOOLEAN,
    figi TEXT,
    cik BIGINT,
);

-- intraday minute level data
CREATE TABLE IF NOT EXISTS security_data (
    security_id INTEGER,
    date TIMESTAMP (0) WITHOUT TIME ZONE,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume INTEGER,
    notional NUMERIC,
    trades INTEGER

    FOREIGN KEY (security_id) REFERENCES security_info (security_id)
);
-- chunk_time_interval should be set s.t. it represents ~= 25% of available RAM
SELECT create_hypertable('security_data', 'date', chunk_time_interval => INTERVAL '2 months');
CREATE INDEX ON security_data (security_id, date ASC);
-- setup initial cluster
CLUSTER security_data USING security_data_security_id_date_idx;
