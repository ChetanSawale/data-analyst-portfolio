"""ATM cash-demand EDA — which ATMs need cash, and when.

Reads the cleaned table produced by the SQL project (atm.db) — or falls back
to rebuilding it from the raw CSV — then answers four operational questions
with pandas + matplotlib. Charts are saved to charts/ and embedded in the
Jupyter notebook (notebook.ipynb).
"""
import os
import sqlite3
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
SQL_PROJ = os.path.join(HERE, "..", "atm-data-quality-sql")
DB = os.path.join(SQL_PROJ, "atm.db")
CHARTS = os.path.join(HERE, "charts")
os.makedirs(CHARTS, exist_ok=True)

plt.rcParams.update({"figure.figsize": (10, 5), "figure.dpi": 110})


def load_clean() -> pd.DataFrame:
    if os.path.exists(DB):
        con = sqlite3.connect(DB)
        df = pd.read_sql("SELECT * FROM clean", con)
        con.close()
        return df
    # fallback: rebuild the cleaned table from the raw CSV with the same rules
    raw = pd.read_csv(os.path.join(SQL_PROJ, "atm_transactions_raw.csv"), dtype=str)
    raw = raw.drop_duplicates(subset="txn_id", keep="first")
    region_map = {"mumbai": "Mumbai", "bandra": "Mumbai", "thane": "Thane", "navi mumbai": "Navi Mumbai"}
    df = pd.DataFrame({
        "txn_id": raw["txn_id"],
        "atm_id": raw["atm_id"],
        "region": raw["region"].str.strip().str.lower().map(region_map).fillna("Other"),
        "txn_date": pd.to_datetime(raw["txn_date"]),
        "txn_time": raw["txn_time"],
        "txn_type": raw["txn_type"].replace({"CASH WITHDRAWL": "CASH_WITHDRAWAL"}),
        "amount": pd.to_numeric(raw["amount"], errors="coerce"),
        "status": raw["status"].str.strip().str.upper(),
        "error_code": raw["error_code"].str.strip().replace("", pd.NA),
    })
    df.loc[df["amount"] < 0, "amount"] = pd.NA
    df = df[df["txn_date"] <= "2026-09-29"].reset_index(drop=True)
    return df


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, name), bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


def main():
    df = load_clean()
    wd = df[df["txn_type"] == "CASH_WITHDRAWAL"].copy()
    ok_wd = wd[wd["status"] == "SUCCESS"].copy()
    ok_wd["txn_date"] = pd.to_datetime(ok_wd["txn_date"])
    ok_wd["hour"] = ok_wd["txn_time"].str.slice(0, 2).astype(int)

    print(f"clean rows: {len(df):,} | successful withdrawals: {len(ok_wd):,}")

    # Q1 — daily cash demand trend (7-day rolling average)
    daily = ok_wd.groupby("txn_date")["amount"].sum() / 1000  # Rs thousands
    fig, ax = plt.subplots()
    ax.plot(daily.index, daily.values, alpha=0.35, label="daily")
    ax.plot(daily.index, daily.rolling(7, min_periods=1).mean().values, lw=2.5, label="7-day avg")
    ax.set_title("Daily cash outflow (Rs thousands) — 60 days, 40 ATMs")
    ax.set_xlabel("Date"); ax.set_ylabel("Rs thousands")
    ax.legend()
    save(fig, "01_daily_cash_demand.png")

    # Q2 — hourly withdrawal pattern: when do ATMs run dry?
    hourly = ok_wd.groupby("hour").size()
    fig, ax = plt.subplots()
    ax.bar(hourly.index, hourly.values, color="#1f77b4")
    ax.set_title("Withdrawals by hour of day — cash-loading windows")
    ax.set_xlabel("Hour"); ax.set_ylabel("Successful withdrawals")
    ax.set_xticks(range(0, 24, 2))
    save(fig, "02_hourly_pattern.png")

    # Q3 — failure rate by region
    fail = df.assign(is_fail=(df["status"] != "SUCCESS").astype(int)).groupby("region").agg(
        txns=("is_fail", "size"), fail_pct=("is_fail", "mean"))
    fail["fail_pct"] = fail["fail_pct"] * 100
    fail = fail.reset_index().sort_values("fail_pct", ascending=False)
    fig, ax = plt.subplots()
    ax.barh(fail["region"], fail["fail_pct"], color="#d62728")
    ax.set_title("Transaction failure rate by region")
    ax.set_xlabel("Failure %")
    for i, v in enumerate(fail["fail_pct"]):
        ax.text(v + 0.2, i, f"{v:.1f}%", va="center")
    save(fig, "03_failure_by_region.png")

    # Q4 — 10 worst ATMs by failure rate (min 20 txns): maintenance priority list
    atm = df.assign(is_fail=(df["status"] != "SUCCESS").astype(int)).groupby("atm_id").agg(
        txns=("is_fail", "size"), fail_pct=("is_fail", "mean"))
    atm["fail_pct"] = atm["fail_pct"] * 100
    atm = atm.reset_index()
    worst = atm[atm["txns"] >= 20].sort_values("fail_pct", ascending=False).head(10)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(worst["atm_id"][::-1], worst["fail_pct"][::-1], color="#ff7f0e")
    ax.set_title("Top 10 ATMs by failure rate (min 20 transactions)")
    ax.set_xlabel("Failure %")
    save(fig, "04_worst_atms.png")

    # Q5 — withdrawal amount distribution
    fig, ax = plt.subplots()
    ax.hist(ok_wd["amount"].dropna(), bins=[0, 500, 1000, 2000, 5000, 10000, 20000],
            edgecolor="white", color="#2ca02c")
    ax.set_title("Withdrawal amount distribution")
    ax.set_xlabel("Amount (Rs)"); ax.set_ylabel("Count")
    save(fig, "05_amount_distribution.png")

    # Console summary for the README
    print("\nKey findings:")
    print(f"- Busiest day: {daily.idxmax().date()} (Rs {daily.max()*1000:,.0f}); quietest: {daily.idxmin().date()}")
    print(f"- Peak hours: {', '.join(str(h) for h in hourly.sort_values(ascending=False).head(3).index)}")
    print(f"- Worst region: {fail.iloc[0]['region']} ({fail.iloc[0]['fail_pct']:.1f}% failures)")
    print(f"- Worst ATM: {worst.iloc[0]['atm_id']} ({worst.iloc[0]['fail_pct']:.1f}% over {worst.iloc[0]['txns']} txns)")
    print(f"- Median withdrawal: Rs {ok_wd['amount'].median():,.0f}")


if __name__ == "__main__":
    main()
