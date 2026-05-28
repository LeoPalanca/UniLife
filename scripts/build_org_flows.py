from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from unilife.cities import build_ka1_he_studies_org_flow_levels


def main() -> None:
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    flow_levels, diagnostics = build_ka1_he_studies_org_flow_levels()
    country_to_uni = flow_levels["country_to_uni"]
    uni_to_country = flow_levels["uni_to_country"]
    uni_to_uni = flow_levels["uni_to_uni"]

    country_to_uni.to_csv(output_dir / "erasmus_country_uni_flows_long.csv", index=False)
    uni_to_country.to_csv(output_dir / "erasmus_uni_country_flows_long.csv", index=False)
    uni_to_uni.to_csv(output_dir / "erasmus_uni_uni_flows_long.csv", index=False)

    # Compatibility filename used by the dashboard.
    country_to_uni.to_csv(output_dir / "erasmus_org_flows_long.csv", index=False)

    print(f"country -> uni rows: {len(country_to_uni):,}")
    print(f"uni -> country rows: {len(uni_to_country):,}")
    print(f"uni -> uni rows: {len(uni_to_uni):,}")
    print(f"country -> uni flow count: {country_to_uni['flow_count'].sum():,}")
    print(f"uni -> country flow count: {uni_to_country['flow_count'].sum():,}")
    print(f"uni -> uni flow count: {uni_to_uni['flow_count'].sum():,}")
    print(f"distinct sending orgs: {uni_to_country['sending_org'].nunique():,}")
    print(f"distinct receiving orgs: {country_to_uni['receiving_org'].nunique():,}")
    print(diagnostics.to_string(index=False))


if __name__ == "__main__":
    main()
