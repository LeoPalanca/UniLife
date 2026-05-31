from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.cities import build_ka1_he_studies_city_flows


def main() -> None:
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    flows, diagnostics = build_ka1_he_studies_city_flows()
    flows.to_csv(output_dir / "erasmus_city_flows_long.csv", index=False)

    print(f"city flow rows: {len(flows):,}")
    print(f"flow count: {flows['flow_count'].sum():,}")
    print(f"distinct receiving cities: {flows['receiving_city'].nunique():,}")
    print(diagnostics.to_string(index=False))


if __name__ == "__main__":
    main()
