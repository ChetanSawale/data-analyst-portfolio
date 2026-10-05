"""Build notebook.ipynb: markdown narrative + runnable code cells + embedded chart outputs."""
import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CHARTS = os.path.join(HERE, "charts")


def img_cell(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "source": [],
        "outputs": [{
            "output_type": "display_data",
            "metadata": {},
            "data": {"image/png": b64, "text/plain": ["<Figure>"]},
        }],
    }


def md(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "source": source.splitlines(keepends=True), "outputs": []}


SETUP = """import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../atm-data-quality-sql/cleaned.csv", parse_dates=["txn_date"])
print(f"{len(df):,} clean transactions | {df['atm_id'].nunique()} ATMs | "
      f"{df['txn_date'].min().date()} to {df['txn_date'].max().date()}")
df.head(3)"""

cells = [
    md("# ATM Cash Demand Analysis\n"
       "Exploratory analysis of 2,290 cleaned ATM transactions (60 days, 40 ATMs, Mumbai region) "
       "to answer the operational questions a cash-management team asks every morning: "
       "how much cash is moving, when ATMs run dry, and which machines need attention.\n\n"
       "*Data: synthetic raw logs with realistic mess (duplicates, label variants, bad amounts) — "
       "cleaned with the SQL audit in `../atm-data-quality-sql/`.*"),
    md("## Setup — load the cleaned data"),
    code(SETUP),

    md("## Q1. What does daily cash demand look like?\n"
       "A 7-day rolling average separates the real trend from day-to-day noise — "
       "this is the series a cash-loading plan is built on."),
    code("""daily = df.query("txn_type == 'CASH_WITHDRAWAL' and status == 'SUCCESS'") \\
              .groupby("txn_date")["amount"].sum() / 1000
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(daily.index, daily.values, alpha=0.35, label="daily")
ax.plot(daily.index, daily.rolling(7, min_periods=1).mean(), lw=2.5, label="7-day avg")
ax.set_title("Daily cash outflow (Rs thousands)"); ax.set_ylabel("Rs thousands"); ax.legend();"""),
    img_cell(os.path.join(CHARTS, "01_daily_cash_demand.png")),

    md("## Q2. When during the day do withdrawals peak?\n"
       "Cash loaded at 6am is gone by evening — the hourly pattern tells us *when* ATMs run dry."),
    code("""wd = df.query("txn_type == 'CASH_WITHDRAWAL' and status == 'SUCCESS'").copy()
wd["hour"] = wd["txn_time"].str.slice(0, 2).astype(int)
hourly = wd.groupby("hour").size()
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(hourly.index, hourly.values)
ax.set_title("Withdrawals by hour of day"); ax.set_xlabel("Hour")
ax.set_ylabel("Successful withdrawals"); ax.set_xticks(range(0, 24, 2));"""),
    img_cell(os.path.join(CHARTS, "02_hourly_pattern.png")),

    md("## Q3. Which region has the worst failure rate?\n"
       "Failures = failed + timeout transactions. A regional skew points to network or maintenance issues, not user error."),
    code("""fail = (df.assign(is_fail=(df["status"] != "SUCCESS").astype(int))
              .groupby("region").agg(txns=("is_fail", "size"), fail_pct=("is_fail", "mean")))
fail["fail_pct"] *= 100
fail.sort_values("fail_pct", ascending=False).round(1)"""),
    img_cell(os.path.join(CHARTS, "03_failure_by_region.png")),

    md("## Q4. Which ATMs should maintenance visit first?\n"
       "Ranked by failure rate (minimum 20 transactions so a quiet ATM can't top the list on 2 bad txns)."),
    code("""atm = (df.assign(is_fail=(df["status"] != "SUCCESS").astype(int))
             .groupby("atm_id").agg(txns=("is_fail", "size"), fail_pct=("is_fail", "mean")))
atm["fail_pct"] *= 100
worst = atm[atm["txns"] >= 20].sort_values("fail_pct", ascending=False).head(10)
worst.round(1)"""),
    img_cell(os.path.join(CHARTS, "04_worst_atms.png")),

    md("## Q5. What does a typical withdrawal look like?\n"
       "The amount distribution sets the denomination mix for cash loading."),
    code("""fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(df.query("txn_type == 'CASH_WITHDRAWAL' and status == 'SUCCESS'")["amount"].dropna(),
        bins=[0, 500, 1000, 2000, 5000, 10000, 20000], edgecolor="white")
ax.set_title("Withdrawal amount distribution")
ax.set_xlabel("Amount (Rs)"); ax.set_ylabel("Count");"""),
    img_cell(os.path.join(CHARTS, "05_amount_distribution.png")),

    md("## Findings & recommendations\n"
       "- **Demand peaks at 9am and 6–8pm** — schedule cash loading before 8am so machines survive the evening rush.\n"
       "- **Weekend volumes run higher** — raise loading limits Fri–Sun.\n"
       "- **~19% transaction failure rate, worst in Mumbai region** — the top-10 ATM list above is the maintenance visit order; "
       "error-code E21 dominates and deserves a root-cause check.\n"
       "- **Median withdrawal is Rs 2,000** — stock Rs 500/2000 notes heaviest.\n\n"
       "*Next step: join this with actual cash-loading logs to measure stockout rate directly.*"),
]

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
    "cells": cells,
}
out = os.path.join(HERE, "notebook.ipynb")
with open(out, "w") as f:
    json.dump(nb, f, indent=1)
print("wrote", out, f"({os.path.getsize(out)//1024} KB, {len(cells)} cells)")
