from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from unilife.indicators import fetch_country_indicators, indicator_coverage, join_indicators
from unilife.grants import grant_coverage, join_sender_grants, load_he_grants


def main() -> None:
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    flows = pd.read_csv(output_dir / "ka1_he_studies_flows_long.csv")
    indicators = fetch_country_indicators(year=2022)
    grants = load_he_grants(call_year=2022)
    joined = join_indicators(flows, indicators)
    joined = join_sender_grants(joined, grants)
    coverage = pd.concat([indicator_coverage(joined), grant_coverage(joined)], ignore_index=True)

    indicators.to_csv(output_dir / "country_indicators_2022.csv", index=False)
    grants.to_csv(output_dir / "he_grants_2022.csv", index=False)
    joined.to_csv(output_dir / "ka1_he_studies_flows_with_indicators.csv", index=False)
    coverage.to_csv(output_dir / "indicator_coverage_diagnostics.csv", index=False)

    print(f"indicator countries: {len(indicators):,}")
    print(f"grant countries: {len(grants):,}")
    print(f"joined rows: {len(joined):,}")
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
