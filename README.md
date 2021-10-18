# Securities database for intraday returns

Python scripts to store and update minute level security price data sourced from the [IEX Cloud API](https://iexcloud.io/) endpoint and stored in a PostgreSQL database.  

## Contents
- [General info](#general-info)
- [DB structure](#db-structure)

## General info

1. IEX API keys and the PostgreSQL password are accessed in the `db_update/references/keys.py` file using environmental variables. Should be stored with the following variable names:
- `PSQL_KEY` PostgreSQL password
- `IEX_SECRET_KEY` Primary IEX API key
- `IEX_TEST_KEY` IEX API key for testing
2. The database has two main tables which are described in `db_setup/setup_securities_tbls.sql` and [shown below](#db-structure).  
- `security_info` contains the meta-data for each security.  `security_id` is the unique security identifier used between the info and data tables and remains constant across trading symbol changes.  
- `security_data` contains intraday price data for all securities listed in `security_info`.  It uses [TimescaleDB](https://www.timescale.com/) for easier time-series data processing.  Timescale chunks data by a manually set time interval.  They recommend that the time chunk interval represent approximately 25% of available RAM so you need to do some testing to optimize read/write operations to the database given your specific data and machine.  For example, I've found that for 8 data points / security / day, about 2 months of data takes up about 0.5 Gb which is ~25% of the RAM on an Azure virtual machine with 2 Gb.  
3. Big thank you to following sources for help on faster PostgreSQL execution:
- https://stackoverflow.com/questions/12593576/adapt-an-iterator-to-behave-like-a-file-like-object-in-python/12604375#12604375
- https://hakibenita.com/fast-load-data-python-postgresql

## DB structure
```
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
```
