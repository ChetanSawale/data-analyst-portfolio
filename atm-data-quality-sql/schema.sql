-- Schema for the raw import. Amounts stay TEXT on import because the raw
-- file mixes blanks and (bad) negatives; we cast after profiling.
DROP TABLE IF EXISTS raw;
CREATE TABLE raw (
  txn_id     TEXT,
  atm_id     TEXT,
  region     TEXT,
  txn_date   TEXT,
  txn_time   TEXT,
  txn_type   TEXT,
  amount     TEXT,
  status     TEXT,
  error_code TEXT
);
