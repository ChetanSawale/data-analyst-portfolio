-- =====================================================================
-- ATM Transaction Data Quality Audit
-- Raw ATM logs (2,368 rows, 60 days, 40 ATMs) -> profile -> clean -> analyze
-- Run:  ./run.sh   (needs the sqlite3 CLI)
-- =====================================================================

.headers on
.mode column

.print ''
.print '================ 1. PROFILING THE RAW DATA ================'

.print ''
.print '-- 1a. Volume and date range'
SELECT COUNT(*) AS total_rows, MIN(txn_date) AS min_date, MAX(txn_date) AS max_date FROM raw;

.print ''
.print '-- 1b. Duplicate txn_ids (a reconciliation risk)'
SELECT COUNT(*) AS duplicate_txn_ids FROM (SELECT txn_id FROM raw GROUP BY txn_id HAVING COUNT(*) > 1);
SELECT txn_id, COUNT(*) AS occurrences FROM raw GROUP BY txn_id HAVING COUNT(*) > 1 ORDER BY occurrences DESC LIMIT 5;

.print ''
.print '-- 1c. Null / blank rates'
SELECT
  SUM(CASE WHEN amount IS NULL OR TRIM(amount) = '' THEN 1 ELSE 0 END) AS blank_amount,
  SUM(CASE WHEN status IS NULL OR TRIM(status) = '' THEN 1 ELSE 0 END) AS blank_status,
  SUM(CASE WHEN error_code IS NULL OR TRIM(error_code) = '' THEN 1 ELSE 0 END) AS blank_error_code,
  COUNT(*) AS total
FROM raw;

.print ''
.print '-- 1d. Label chaos: distinct raw values'
SELECT DISTINCT region   AS region_variants FROM raw ORDER BY 1;
SELECT DISTINCT status   AS status_variants FROM raw ORDER BY 1;
SELECT DISTINCT txn_type AS type_variants   FROM raw ORDER BY 1;

.print ''
.print '-- 1e. Out-of-range values'
SELECT COUNT(*) AS negative_amounts FROM raw WHERE CAST(amount AS REAL) < 0;
SELECT COUNT(*) AS future_dated_rows FROM raw WHERE txn_date > '2026-09-29';
SELECT COUNT(*) AS failed_without_error_code
FROM raw WHERE UPPER(TRIM(status)) = 'FAILED' AND (error_code IS NULL OR TRIM(error_code) = '');

.print ''
.print '================ 2. CLEANING ================'
.print 'Rules: keep first occurrence of each txn_id; standardise region /'
.print 'status / type labels; null out negative amounts; drop future dates.'

DROP TABLE IF EXISTS clean;
CREATE TABLE clean AS
WITH deduped AS (
  SELECT r.*, ROW_NUMBER() OVER (PARTITION BY txn_id ORDER BY txn_date, txn_time) AS rn
  FROM raw r
),
standardized AS (
  SELECT
    txn_id,
    atm_id,
    CASE
      WHEN TRIM(LOWER(region)) IN ('mumbai', 'bandra') THEN 'Mumbai'
      WHEN TRIM(LOWER(region)) = 'thane'              THEN 'Thane'
      WHEN TRIM(LOWER(region)) = 'navi mumbai'        THEN 'Navi Mumbai'
      ELSE 'Other'
    END AS region,
    txn_date,
    txn_time,
    CASE WHEN txn_type = 'CASH WITHDRAWL' THEN 'CASH_WITHDRAWAL' ELSE txn_type END AS txn_type,
    CASE WHEN CAST(amount AS REAL) < 0 THEN NULL ELSE CAST(amount AS REAL) END AS amount,
    UPPER(TRIM(status)) AS status,
    NULLIF(TRIM(error_code), '') AS error_code
  FROM deduped
  WHERE rn = 1
)
SELECT * FROM standardized WHERE txn_date <= '2026-09-29';

.print ''
.print '-- 2a. Retention after cleaning'
SELECT (SELECT COUNT(*) FROM raw) AS raw_rows,
       (SELECT COUNT(*) FROM clean) AS clean_rows,
       ROUND(100.0 * (SELECT COUNT(*) FROM clean) / (SELECT COUNT(*) FROM raw), 1) AS retention_pct;

.print ''
.print '================ 3. ANALYSIS ================'

.print ''
.print '-- 3a. Failure rate by region (where should maintenance go first?)'
SELECT region,
       COUNT(*) AS txns,
       ROUND(100.0 * SUM(CASE WHEN status <> 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 1) AS fail_pct
FROM clean GROUP BY region ORDER BY fail_pct DESC;

.print ''
.print '-- 3b. 10 worst ATMs by failure rate (min 20 transactions)'
SELECT atm_id,
       COUNT(*) AS txns,
       ROUND(100.0 * SUM(CASE WHEN status <> 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 1) AS fail_pct
FROM clean GROUP BY atm_id HAVING COUNT(*) >= 20 ORDER BY fail_pct DESC LIMIT 10;

.print ''
.print '-- 3c. Daily cash outflow (for cash-loading / replenishment planning)'
SELECT txn_date,
       COUNT(*) AS withdrawals,
       CAST(SUM(amount) AS INT) AS cash_out_rs
FROM clean
WHERE txn_type = 'CASH_WITHDRAWAL' AND status = 'SUCCESS'
GROUP BY txn_date ORDER BY txn_date LIMIT 7;
.print '... (full 60-day series in the table)'

.print ''
.print '-- 3d. Top error codes'
SELECT error_code, COUNT(*) AS occurrences
FROM clean WHERE error_code IS NOT NULL GROUP BY error_code ORDER BY occurrences DESC;

.print ''
.print '-- 3e. Peak withdrawal hours'
SELECT CAST(SUBSTR(txn_time, 1, 2) AS INTEGER) AS hour,
       COUNT(*) AS withdrawals
FROM clean
WHERE txn_type = 'CASH_WITHDRAWAL' AND status = 'SUCCESS'
GROUP BY hour ORDER BY withdrawals DESC LIMIT 5;

.print ''
.print '-- 3f. Weekend vs weekday failure rate'
SELECT CASE WHEN CAST(STRFTIME('%w', txn_date) AS INTEGER) IN (0, 6) THEN 'weekend' ELSE 'weekday' END AS day_type,
       COUNT(*) AS txns,
       ROUND(100.0 * SUM(CASE WHEN status <> 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 1) AS fail_pct
FROM clean GROUP BY day_type;
