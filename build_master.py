"""Build data/MasterFile.csv from all raw Money Manager exports.

Merges every file in data/raw/ (csv + xlsx), normalises schema, dedupes
overlapping rows, derives Year/Month, sorts by Date, and writes the master.

Re-run any time a new export is dropped into data/raw/ — output is fully
reproducible. Do NOT hand-edit MasterFile.csv; edit the raw exports instead.

Enhancement files (all optional — pipeline runs without them):
- category_map.csv       raw,canonical  — rename categories
- account_map.csv        raw,canonical  — rename accounts
- subcategory_promote.csv  from_category,from_subcategory,to_category,to_subcategory
                           — promote subcategory-typed rows out of catch-all
- note_patterns.csv      pattern,new_category,new_subcategory
                           — regex on Note to classify Other/Other rows

Output columns (MasterFile.csv):
  Date, Year, Month, Account, Category, Subcategory, Note, MYR,
  Income/Expense, EntryType, RecurringFlag

Also writes data/quality_report.csv after each build.

Notes / known limitations:
- Raw exports overlap heavily. The 23-06-2025 export stores DATE ONLY (no
  time), so its rows are degraded duplicates of timed rows in the xlsx/other
  exports. Those are dropped via a date-level "loose key" match.
- Category/Account names drift across exports (emoji prefixes, renames like
  "Food & Drink" -> "Food", "Dompet" -> "Cash"). Harmonised here: emoji are
  stripped, then category_map.csv / account_map.csv apply explicit renames.
  Edit those map files (raw,canonical) to add/adjust mappings.
- EntryType column tags rows: "Adjustment" (Modified Bal. balance fixes),
  "Transfer" (Transfer-* between accounts), "Normal" (real income/expense).
  Filter EntryType == "Normal" for spending/income analysis.
- RecurringFlag: True when (Category, Subcategory) combo appears in 3+ distinct
  calendar months. Identifies subscriptions and habitual expense types.
"""

import re
from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
RAW_DIR   = BASE / "data" / "raw"
OUT_FILE  = BASE / "data" / "MasterFile.csv"
QR_FILE   = BASE / "data" / "quality_report.csv"


# ── Map loaders ────────────────────────────────────────────────────────────

def _load_map(name: str) -> dict:
    path = BASE / name
    if not path.exists():
        return {}
    m = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    return {r.raw.strip(): r.canonical.strip() for r in m.itertuples()}


def _load_subcategory_promote(name: str) -> list:
    path = BASE / name
    if not path.exists():
        return []
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("").to_dict("records")


def _load_note_patterns(name: str) -> list:
    path = BASE / name
    if not path.exists():
        return []
    rows = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("").to_dict("records")
    return [
        {"re": re.compile(r["pattern"]),
         "new_category": r["new_category"],
         "new_subcategory": r["new_subcategory"]}
        for r in rows
    ]


CAT_MAP         = _load_map("category_map.csv")
ACCT_MAP        = _load_map("account_map.csv")
SUBCAT_PROMOTE  = _load_subcategory_promote("subcategory_promote.csv")
NOTE_PATTERNS   = _load_note_patterns("note_patterns.csv")
_EMOJI          = re.compile(r"[^\x00-\x7F]+")


# ── Cleaning helpers ───────────────────────────────────────────────────────

def clean_category(s: str) -> str:
    s = _EMOJI.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = CAT_MAP.get(s, s)
    return ACCT_MAP.get(s, s)


def clean_account(s: str) -> str:
    return ACCT_MAP.get(s.strip(), s.strip())


# ── Enrichment steps ───────────────────────────────────────────────────────

def apply_subcategory_promotions(df: pd.DataFrame) -> pd.DataFrame:
    """Promote rows out of 'Other' when the subcategory already names a type.

    E.g.  Category=Other, Subcategory=Movies  →  Category=Entertainment
    Rules defined in subcategory_promote.csv.
    """
    for rule in SUBCAT_PROMOTE:
        mask = (
            (df["Category"] == rule["from_category"]) &
            (df["Subcategory"] == rule["from_subcategory"])
        )
        if mask.any():
            df.loc[mask, "Category"] = rule["to_category"]
            if rule.get("to_subcategory"):
                df.loc[mask, "Subcategory"] = rule["to_subcategory"]
    return df


def apply_note_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Auto-categorize residual Other/Other rows by matching Note against regexes.

    Patterns applied in order; first match wins per row.
    Rules defined in note_patterns.csv.
    """
    if not NOTE_PATTERNS:
        return df
    uncategorized = (
        (df["Category"] == "Other") &
        (df["Subcategory"].isin(["Other", "", "other"]))
    )
    for rule in NOTE_PATTERNS:
        if not uncategorized.any():
            break
        matched = uncategorized & df["Note"].map(
            lambda n, _r=rule["re"]: bool(_r.search(n)) if isinstance(n, str) else False
        )
        if matched.any():
            df.loc[matched, "Category"] = rule["new_category"]
            if rule["new_subcategory"]:
                df.loc[matched, "Subcategory"] = rule["new_subcategory"]
            uncategorized = uncategorized & ~matched
    return df


def add_recurring_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows whose (Category, Subcategory) combo spans 3+ distinct months.

    True = habitual / subscription-like expense type.
    Computed across all Normal rows so income recurring patterns are captured too.
    """
    ym = df["Date"].dt.to_period("M")
    month_counts = (
        df.assign(_ym=ym)
        .groupby(["Category", "Subcategory"])["_ym"]
        .nunique()
        .rename("_mc")
        .reset_index()
    )
    df = df.merge(month_counts, on=["Category", "Subcategory"], how="left")
    df["RecurringFlag"] = df["_mc"].fillna(0) >= 3
    return df.drop(columns=["_mc"])


def generate_quality_report(df: pd.DataFrame) -> None:
    """Write data/quality_report.csv with per-category data quality metrics."""
    exp = df[(df["EntryType"] == "Normal") & (df["Income/Expense"] == "Expense")].copy()
    exp["_blank_sub"] = exp["Subcategory"].isin(["", "Other"])
    exp["_blank_note"] = exp["Note"] == ""
    grp = exp.groupby("Category")
    report = pd.DataFrame({
        "TxnCount":          grp["MYR"].count(),
        "TotalMYR":          grp["MYR"].sum().round(2),
        "AvgMYR":            grp["MYR"].mean().round(2),
        "StdMYR":            grp["MYR"].std().round(2),
        "BlankSubcatPct":    (grp["_blank_sub"].mean() * 100).round(1),
        "BlankNotePct":      (grp["_blank_note"].mean() * 100).round(1),
    }).sort_values("TotalMYR", ascending=False).reset_index()
    report.to_csv(QR_FILE, index=False, encoding="utf-8-sig")
    print(f"  Quality report  -> {QR_FILE}")


# ── Raw file ingestion ─────────────────────────────────────────────────────

CORE = ["Date", "Account", "Category", "Subcategory", "Note", "MYR", "Income/Expense"]
KEY  = ["DateOnly", "Account", "Category", "Subcategory", "Note", "MYR", "Income/Expense"]


def read_raw(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df = df[[c for c in CORE if c in df.columns]].copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df["MYR"]  = pd.to_numeric(df["MYR"], errors="coerce")
    for c in ["Account", "Category", "Subcategory", "Note", "Income/Expense"]:
        df[c] = df[c].fillna("").str.strip()
    df["Account"]  = df["Account"].map(clean_account)
    df["Category"] = df["Category"].map(clean_category)
    df = df.dropna(subset=["Date", "MYR"])
    df["Date"]     = df["Date"].dt.floor("s")
    df["HasTime"]  = df["Date"].dt.time != pd.Timestamp("00:00:00").time()
    df["DateOnly"] = df["Date"].dt.normalize()
    df["__src"]    = path.name
    return df


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    files = sorted(RAW_DIR.glob("*.csv")) + sorted(RAW_DIR.glob("*.xlsx"))
    if not files:
        raise SystemExit(f"No raw files in {RAW_DIR}")

    frames = [read_raw(f) for f in files]
    for f, df in zip(files, frames):
        print(f"  {f.name}: {len(df)} rows  ({df['Date'].min()} -> {df['Date'].max()})")
    allrows = pd.concat(frames, ignore_index=True)

    timed    = allrows[allrows["HasTime"]].copy()
    dateonly = allrows[~allrows["HasTime"]].copy()

    timed = timed.drop_duplicates(subset=CORE)
    timed_keys = set(map(tuple, timed[KEY].values))
    mask = [tuple(r) not in timed_keys for r in dateonly[KEY].values]
    dateonly = dateonly[mask].drop_duplicates(subset=CORE)

    master = pd.concat([timed, dateonly], ignore_index=True)
    master = master.sort_values("Date").reset_index(drop=True)

    master["Year"]  = master["Date"].dt.year
    master["Month"] = master["Date"].dt.month

    ie = master["Income/Expense"]
    master["EntryType"] = "Normal"
    master.loc[ie.str.startswith("Transfer"),          "EntryType"] = "Transfer"
    master.loc[master["Category"] == "Modified Bal.",  "EntryType"] = "Adjustment"

    # ── Enrichment ─────────────────────────────────────────────────────────
    before_other = (master["Category"] == "Other").sum()
    master = apply_subcategory_promotions(master)
    master = apply_note_patterns(master)
    after_other = (master["Category"] == "Other").sum()
    print(f"\n  Reclassified {before_other - after_other} rows out of 'Other' "
          f"({before_other} -> {after_other} remaining)")

    master = add_recurring_flag(master)
    generate_quality_report(master)

    out = master[["Date", "Year", "Month", "Account", "Category", "Subcategory",
                  "Note", "MYR", "Income/Expense", "EntryType", "RecurringFlag"]]
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print(f"\n  Wrote {len(out)} rows -> {OUT_FILE}")
    print(f"  Range: {out['Date'].min()} -> {out['Date'].max()}")
    print(f"  Dropped {len(allrows) - len(out)} duplicate/degraded rows "
          f"(from {len(allrows)} total raw)")


if __name__ == "__main__":
    main()
