#!/bin/bash
# One-shot runner: builds atm.db from the raw CSV and runs the full audit.
set -e
cd "$(dirname "$0")"
rm -f atm.db
sqlite3 atm.db < schema.sql
sqlite3 atm.db <<'EOF'
.mode csv
.import --skip 1 atm_transactions_raw.csv raw
EOF
sqlite3 atm.db < data_quality_audit.sql
