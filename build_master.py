"""Build data/MasterFile.csv from all raw Money Manager exports.

Merges every file in data/raw/ (csv + xlsx), normalises schema, dedupes
overlapping rows, derives Year/Month, sorts by Date, and writes the master.

Re-run any time a new export is dropped into data/raw/ — output is fully
reproducible. Do NOT hand-edit MasterFile.csv; edit the raw exports instead.

Notes / known limitations:
- Raw exports overlap heavily. The 23-06-2025 export stores DATE ONLY (no
  time), so its rows are degraded duplicates of timed rows in the xlsx/other
  exports. Those are dropped via a date-level "loose key" match.
- Category/Account names drift across exports (e.g. "Food & Drink" -> "Food",
  "Dompet" -> "Cash", later names carry emojis). This script does NOT
  harmonise them — clean categories downstream if needed.
"""

from pathlib import Path
import pandas as pd

RAW_DIR = Path(__file__).parent / "data" / "raw"
OUT_FILE = Path(__file__).parent / "data" / "MasterFile.csv"

# Canonical columns kept in the master (raw col 11 / Description / Amount /
# Currency are dropped: Amount duplicates MYR, Currency is always MYR, col 11
# is a junk duplicate of MYR renamed Account2/Note2/Account3 across exports).
CORE = ["Date", "Account", "Category", "Subcategory", "Note", "MYR", "Income/Expense"]
KEY = ["DateOnly", "Account", "Category", "Subcategory", "Note", "MYR", "Income/Expense"]


def read_raw(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df = df[[c for c in CORE if c in df.columns]].copy()
    # Parse mixed date formats: "d/m/Y", "dd/mm/Y HH:MM:SS", and real datetimes.
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df["MYR"] = pd.to_numeric(df["MYR"], errors="coerce")
    for c in ["Account", "Category", "Subcategory", "Note", "Income/Expense"]:
        df[c] = df[c].fillna("").str.strip()
    df = df.dropna(subset=["Date", "MYR"])
    # Floor to seconds: the xlsx export carries microseconds the csv exports
    # lack, which would otherwise defeat exact dedupe of the same transaction.
    df["Date"] = df["Date"].dt.floor("s")
    df["HasTime"] = df["Date"].dt.time != pd.Timestamp("00:00:00").time()
    df["DateOnly"] = df["Date"].dt.normalize()
    df["__src"] = path.name
    return df


def main() -> None:
    files = sorted(RAW_DIR.glob("*.csv")) + sorted(RAW_DIR.glob("*.xlsx"))
    if not files:
        raise SystemExit(f"No raw files in {RAW_DIR}")

    frames = [read_raw(f) for f in files]
    for f, df in zip(files, frames):
        print(f"  {f.name}: {len(df)} rows  ({df['Date'].min()} -> {df['Date'].max()})")
    allrows = pd.concat(frames, ignore_index=True)

    timed = allrows[allrows["HasTime"]].copy()
    dateonly = allrows[~allrows["HasTime"]].copy()

    # 1) Exact-dedupe timed rows (resolves file-to-file overlap).
    timed = timed.drop_duplicates(subset=CORE)

    # 2) Drop date-only rows that already exist as a timed row (same day + same
    #    fields). Keep the rest (transactions no timed export covers).
    timed_keys = set(map(tuple, timed[KEY].values))
    mask = [tuple(r) not in timed_keys for r in dateonly[KEY].values]
    dateonly = dateonly[mask].drop_duplicates(subset=CORE)

    master = pd.concat([timed, dateonly], ignore_index=True)
    master = master.sort_values("Date").reset_index(drop=True)

    master["Year"] = master["Date"].dt.year
    master["Month"] = master["Date"].dt.month
    out = master[["Date", "Year", "Month", "Account", "Category",
                  "Subcategory", "Note", "MYR", "Income/Expense"]]
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print(f"\nWrote {len(out)} rows -> {OUT_FILE}")
    print(f"  range: {out['Date'].min()} -> {out['Date'].max()}")
    print(f"  dropped {len(allrows) - len(out)} duplicate/degraded rows "
          f"(from {len(allrows)} total raw)")


if __name__ == "__main__":
    main()
