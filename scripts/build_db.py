"""Build the SQLite DB from the processed CSV exports.

Each data/processed/*.csv becomes a table named by its file stem. Join keys are
indexed. Rebuild any time with: uv run python scripts/build_db.py
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.db import DB_PATH, get_conn

PROCESSED = Path("data/processed")

# index hints: table stem -> list of column tuples to index (only applied if columns exist)
INDEXES = {
    "ka1_he_studies_flows_with_indicators": [("sending_code", "receiving_code"), ("receiving_code",)],
    "erasmus_city_flows_long": [("sending_code", "receiving_code"), ("receiving_code", "receiving_city")],
    "erasmus_country_year_panel": [("sending_code", "receiving_code", "year"), ("year",)],
    "erasmus_nuts_year_panel": [("origin", "destination", "year"), ("year",)],
    "erasmus_lau_year_panel": [("origin", "destination", "year"), ("year",)],
    "reddit_destination_mentions": [("country",), ("city",)],
    "erasmusu_city_ratings": [("country_code", "city_norm")],
    "city_coordinates": [("receiving_code", "receiving_city")],
    "institution_quality": [("receiving_code", "city_norm")],
    "user_institution_quality": [("receiving_code", "city_norm")],
    "owid_country_year": [("receiving_code", "year")],
    "erasmus_field_flow_panel": [("receiving_code", "isced_broad", "year"), ("sending_code", "receiving_code", "isced_broad", "year")],
    "covid_sector_hit": [("receiving_code", "nace_r2")],
    "covid_employment_hit": [("receiving_code", "nace_r2")],
    "covid_event_study_employment": [("year",)],
    "institution_quality_panel": [("receiving_code", "city_norm", "year")],
    "sector_wage_panel": [("country_code", "nace_code", "year")],
}


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = get_conn()
    csvs = sorted(PROCESSED.glob("*.csv"))
    for path in csvs:
        name = path.stem
        df = pd.read_csv(path)
        df.to_sql(name, conn, if_exists="replace", index=False)
        cols = set(df.columns)
        for spec in INDEXES.get(name, []):
            if set(spec).issubset(cols):
                idx = f"ix_{name}_{'_'.join(spec)}"
                conn.execute(f'CREATE INDEX IF NOT EXISTS "{idx}" ON "{name}" ({", ".join(spec)})')
        print(f"  {name}: {len(df):,} rows, {len(df.columns)} cols")
    conn.commit()
    n = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    conn.close()
    print(f"\n{n} tables written to {DB_PATH} ({DB_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
