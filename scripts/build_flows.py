from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.ka1 import build_ka1_he_studies_flows


def main() -> None:
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    flows, diagnostics = build_ka1_he_studies_flows()
    flows.to_csv(output_dir / "ka1_he_studies_flows_long.csv", index=False)
    diagnostics.to_csv(output_dir / "ka1_he_studies_filter_diagnostics.csv", index=False)

    print(f"flows rows: {len(flows):,}")
    print(f"flow count: {flows['flow_count'].sum():,}")
    print(diagnostics.to_string(index=False))


if __name__ == "__main__":
    main()
