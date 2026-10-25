from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.indicators import fetch_sector_earnings
from erasmusgravity.db import get_conn, write_table


def main() -> None:
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    earnings = fetch_sector_earnings()
    output = output_dir / "sector_earnings_latest.csv"
    earnings.to_csv(output, index=False)
    # Update only the reference table; the historical research tables retain their vintages.
    with get_conn() as conn:
        write_table(earnings, "sector_earnings_latest", conn)
    manifest = {
        "dataset": f"earn_ses{int(earnings['year'].max()) % 100:02d}_24", "year": int(earnings["year"].max()),
        "sourceUrl": f"https://ec.europa.eu/eurostat/databrowser/view/earn_ses{int(earnings['year'].max()) % 100:02d}_24/default/table?lang=en",
        "checkedAt": datetime.now(timezone.utc).date().isoformat(),
        "filters": {"sex": "T", "sizeclas": "GE10", "l_serv": "TOTAL", "indic_se": "ERN", "freq": "A"},
        "units": ["EUR", "PPS"],
        "rows": len(earnings), "countries": int(earnings.loc[earnings.is_sector, "country_code"].nunique()),
        "csvSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "scope": "Mean monthly gross earnings by employer NACE activity, employers with 10+ employees, all sexes and lengths of service. Not earnings by degree subject.",
    }
    Path("docs/sector-earnings-latest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    countries = earnings["country_code"].nunique()
    sectors = int(earnings["is_sector"].sum())
    print(f"rows: {len(earnings):,}")
    print(f"countries: {countries}")
    print(f"detailed sector rows: {sectors}")


if __name__ == "__main__":
    main()
