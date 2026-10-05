"""Generate a realistic-but-messy ATM transaction dataset.

Simulates raw transaction logs collected across regional endpoints — the kind
of data a Reports Executive cleans daily before reporting. Messiness is
injected deterministically (not by chance) so every flaw the audit checks for
is guaranteed present: duplicates, nulls, inconsistent labels, negatives,
future dates, missing error codes.
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)

ATMS = [f"ATM-{1000 + i}" for i in range(40)]
REGIONS_RAW = ["Mumbai", "mumbai ", "MUMBAI", "Bandra", "bandra", "Thane", "thane", "Navi Mumbai", "navi mumbai"]
TYPES = ["CASH_WITHDRAWAL", "BALANCE_ENQUIRY", "MINI_STATEMENT", "TRANSFER", "CASH WITHDRAWL"]  # note the typo variant
STATUSES = ["SUCCESS", "Success", "FAILED", "failed", "TIMEOUT", None]

# Realistic intraday pattern: morning + evening peaks (people withdraw before/after work)
HOURS = list(range(24))
HOUR_W = [2, 1, 1, 1, 2, 3, 5, 7, 9, 10, 9, 8, 7, 6, 6, 7, 8, 10, 11, 10, 8, 6, 4, 3]

start = date(2026, 8, 1)
rows = []
txn = 900000
for day in range(60):
    d = start + timedelta(days=day)
    n = random.randint(25, 45) + (10 if d.weekday() >= 5 else 0)  # weekends busier
    for _ in range(n):
        txn += 1
        ttype = random.choices(TYPES, weights=[55, 20, 10, 10, 5])[0]
        status = random.choices(STATUSES, weights=[70, 10, 8, 5, 5, 2])[0]
        amount = None
        if ttype in ("CASH_WITHDRAWAL", "CASH WITHDRAWL") and status != "FAILED":
            amount = random.choice([500, 1000, 2000, 5000, 10000])
        hour = random.choices(HOURS, weights=HOUR_W)[0]
        minute = random.randint(0, 59)
        err = ""
        if status in ("FAILED", "failed"):
            err = random.choice(["E21", "E45", "E21", "E07"])
        elif status == "TIMEOUT":
            err = "E99"
        rows.append([txn, random.choice(ATMS), random.choice(REGIONS_RAW),
                     d.isoformat(), f"{hour:02d}:{minute:02d}", ttype, amount, status, err])

# --- deterministic mess injection ---------------------------------------
def pick(k):
    return random.sample(range(len(rows)), k)

# 1. duplicate txn_ids (~2%)
for i in pick(int(len(rows) * 0.02)):
    rows.append(list(rows[i]))

# 2. negative amounts on ~30 successful withdrawals (glitch)
c = 0
for r in rows:
    if c >= 30:
        break
    if r[5] in ("CASH_WITHDRAWAL", "CASH WITHDRAWL") and r[6] is not None:
        r[6] = -r[6]
        c += 1

# 3. missing amounts on ~3% of withdrawals
wds = [r for r in rows if r[5] in ("CASH_WITHDRAWAL", "CASH WITHDRAWL") and r[6] is not None]
for r in random.sample(wds, int(len(wds) * 0.03)):
    r[6] = None

# 4. future-dated rows (endpoint clock skew): 15 rows from the last few days
#    pushed past the dataset end date
late = [i for i, r in enumerate(rows) if r[3] >= "2026-09-27"]
for i in random.sample(late, 15):
    r = rows[i]
    dd = date.fromisoformat(r[3]) + timedelta(days=random.randint(1, 3))
    r[3] = dd.isoformat()

# 5. FAILED rows with no error code (logging gap): ~8% of them
failed = [r for r in rows if r[7] in ("FAILED", "failed")]
for r in random.sample(failed, max(1, int(len(failed) * 0.08))):
    r[8] = ""

random.shuffle(rows)
with open("atm_transactions_raw.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["txn_id", "atm_id", "region", "txn_date", "txn_time", "txn_type", "amount", "status", "error_code"])
    w.writerows(rows)
print(f"wrote {len(rows)} rows")
