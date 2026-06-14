# Project Context — Income-Expenditure Data Analysis

> Living document. Read at session start, update at session end.

## What This Project Is

Personal income/expenditure analysis. Data from Money Manager app. Original analysis done in Excel + Power BI (see README Medium links). Now porting to a Streamlit dashboard (WIP).
Stack: Python, Streamlit, pandas, plotly. Entry point: `Main-Page.py` (`streamlit run Main-Page.py`). Multi-page via `pages/`.

## What Was Decided

- Use Streamlit for interactive dashboard — replaces static Excel/Power BI views.
- Data source `data/MasterFile.csv`, consolidated from raw Money Manager exports in `data/raw/`.

## Pending Tasks

- `pages/page2.py` and `pages/page3.py` are empty — build out additional dashboard pages.
- BUG: `Main-Page.py` references `df['Year']` and `df['Month']` (lines 20-21, 26, 32, 37, 55) but `MasterFile.csv` has no `Year`/`Month` columns — only `Date` (format `d/m/YYYY`). App will crash. Derive Year/Month from `Date`.
- Refresh `MasterFile.csv` — newest raw export `Money Manager_14-06-2026.xlsx` not yet merged.

## Key Files

| File | Role |
|---|---|
| `Main-Page.py` | Streamlit home: dataframe view, year slider, category filter, pie + line charts |
| `pages/page2.py`, `pages/page3.py` | Empty placeholders for extra pages |
| `data/MasterFile.csv` | Consolidated master dataset |
| `data/raw/` | Raw Money Manager exports (csv + xlsx) |
| `requirements.txt` | pandas streamlit plotly.express |

## Last Session — 2026-06-14

- Cloned repo from https://github.com/MHafizAzizi/Income-Expenditure-Data-Analysis.git into project folder.
- Bootstrapped `context.md` + `CLAUDE.md` pointer.
- Found Year/Month bug in `Main-Page.py` (recorded in Pending).
