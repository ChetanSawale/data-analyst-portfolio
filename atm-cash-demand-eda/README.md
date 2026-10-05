# ATM Cash Demand Analysis (Python · pandas · matplotlib)

Exploratory data analysis on the 2,290 cleaned ATM transactions from the SQL audit —
answering the operational questions a cash-management team asks every morning.

## Questions & findings

1. **What does daily cash demand look like?** → `01_daily_cash_demand.png` — daily outflow with a
   7-day rolling average; busiest day moved Rs 1,42,000 (2026-08-29).
2. **When do ATMs run dry?** → `02_hourly_pattern.png` — clear peaks at **9am and 6–8pm**;
   cash loaded at 6am is gone by the evening rush.
3. **Which region fails most?** → `03_failure_by_region.png` — Mumbai region at 18.9%.
4. **Which ATMs need maintenance first?** → `04_worst_atms.png` — ATM-1023 at 33.9% failures
   over 56 transactions tops the visit list (min 20 txns filter applied).
5. **What does a typical withdrawal look like?** → `05_amount_distribution.png` — median Rs 2,000;
   stock Rs 500/2000 notes heaviest.

**Recommendations:** load cash before 8am; raise weekend loading limits (weekend volumes run higher);
investigate error-code E21 cluster; schedule maintenance visits in the top-10 ATM order.

## Run it

```bash
python3 analysis.py          # regenerates all charts into charts/
python3 build_notebook.py   # rebuilds notebook.ipynb with embedded chart outputs
```

`notebook.ipynb` renders directly on GitHub with all five charts embedded — no execution needed to read it.

## Files

- `notebook.ipynb` — the full analysis as a readable notebook (charts embedded)
- `analysis.py` — generates the charts from the cleaned data
- `build_notebook.py` — assembles the notebook JSON
- `charts/` — the five output charts (PNG)
