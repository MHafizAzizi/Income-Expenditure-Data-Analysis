# Project Context — Income-Expenditure Data Analysis

> Living document. Read at session start, update at session end.

## What This Project Is

Personal income/expenditure analysis. Data from Money Manager app. Original analysis done in Excel + Power BI (see README Medium links). Codebase being rebuilt from scratch — old Streamlit scripts removed.
Stack: Python (approach TBD). Data only at present.

## What Was Decided

- 2026-06-14: Scrapped old Streamlit dashboard — starting from scratch. Removed `Main-Page.py`, `pages/`, `requirements.txt`.
- Data source `data/MasterFile.csv`, consolidated from raw Money Manager exports in `data/raw/`.

## Pending Tasks

- Decide new approach/stack for analysis (none chosen yet).
- Refresh `MasterFile.csv` — newest raw export `Money Manager_14-06-2026.xlsx` not yet merged.

## Key Files

| File | Role |
|---|---|
| `data/MasterFile.csv` | Consolidated master dataset (cols: Date, Account, Category, Subcategory, Note, MYR, Income/Expense, ...) |
| `data/raw/` | Raw Money Manager exports (csv + xlsx) |

## Last Session — 2026-06-14

- Cloned repo from https://github.com/MHafizAzizi/Income-Expenditure-Data-Analysis.git into project folder.
- Bootstrapped `context.md` + `CLAUDE.md` pointer.
- Removed all Streamlit scripts (`Main-Page.py`, `pages/`, `requirements.txt`) — rebuilding from scratch.
