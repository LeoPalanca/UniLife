from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.indicators import fetch_sector_earnings


def main() -> None:
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    earnings = fetch_sector_earnings(year=2018)
    earnings.to_csv(output_dir / "sector_earnings_2018.csv", index=False)

    countries = earnings["country_code"].nunique()
    sectors = int(earnings["is_sector"].sum())
    print(f"rows: {len(earnings):,}")
    print(f"countries: {countries}")
    print(f"detailed sector rows: {sectors}")


if __name__ == "__main__":
    main()
