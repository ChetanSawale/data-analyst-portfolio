# ATM Transaction Data Quality Audit (SQL)

End-to-end SQL data-quality audit on 2,347 raw ATM transaction logs (60 days, 40 ATMs):
**profile the mess → clean it with documented rules → answer business questions** — the exact
workflow a data analyst runs before any dashboard or report can be trusted.

## The raw data

`atm_transactions_raw.csv` simulates logs collected across regional endpoints, with realistic flaws baked in:

| Flaw | Count found |
|---|---|
| Duplicate `txn_id`s (reconciliation risk) | 44 |
| Region label variants (`Mumbai` / `mumbai ` / `MUMBAI` / `Bandra`…) | 9 → 3 |
| Status label variants (`SUCCESS` / `Success` / `FAILED` / `failed` / `TIMEOUT` / blank) | 6 → 3 |
| Transaction-type typo (`CASH WITHDRAWL`) | 1 variant |
| Negative withdrawal amounts (glitch) | 30 |
| Future-dated rows (endpoint clock skew) | 11 |
| Failed transactions with no error code (logging gap) | 21 |

`generate_data.py` reproduces the dataset deterministically (`random.seed(42)`) — flaws are
injected explicitly so every check in the audit is guaranteed to fire.

## Cleaning rules (all documented in the SQL)

1. Deduplicate on `txn_id`, keeping the first occurrence
2. Standardise region labels (`mumbai`/`bandra` → Mumbai, `thane` → Thane, `navi mumbai` → Navi Mumbai)
3. Uppercase/trim statuses; fix the `CASH WITHDRAWL` typo
4. Null out negative amounts (keep the row — the transaction happened, the amount is unknown)
5. Drop rows dated after the dataset end (`2026-09-29`)

**Result: 2,347 → 2,290 rows (97.6% retention).**

## Business answers

| Question | Answer |
|---|---|
| Which region fails most? | Mumbai 18.9%, Thane 18.5%, Navi Mumbai 18.5% |
| Which ATMs need maintenance first? | ATM-1023 (33.9% failures), ATM-1026 (26.1%), ATM-1028 (25.0%) — full top-10 in the output |
| What are the top error codes? | E99 timeouts (121), E21 (118), E07 (68), E45 (51) |
| When do withdrawals peak? | 9am, 6pm, 8pm — load cash before 8am |
| Weekend vs weekday failures? | Weekday 19.3% vs weekend 17.4% |

## Run it

```bash
./run.sh        # needs the sqlite3 CLI; builds atm.db and runs the full audit
```

Or step by step:

```bash
sqlite3 atm.db < schema.sql
sqlite3 atm.db
sqlite> .mode csv
sqlite> .import --skip 1 atm_transactions_raw.csv raw
sqlite> .read data_quality_audit.sql
```

## Files

- `atm_transactions_raw.csv` — the messy source data (2,347 rows)
- `cleaned.csv` — the cleaned table, exported for the Python EDA project
- `generate_data.py` — deterministic dataset generator
- `schema.sql` — raw table definition
- `data_quality_audit.sql` — the audit: profiling → cleaning → analysis
- `run.sh` — one-shot runner
