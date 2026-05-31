from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.panel import build_panels


def main() -> None:
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    panels = build_panels()
    names = {
        "country_year": "erasmus_country_year_panel.csv",
        "lau_year": "erasmus_lau_year_panel.csv",
        "nuts_year": "erasmus_nuts_year_panel.csv",
    }
    for key, filename in names.items():
        panels[key].to_csv(output_dir / filename, index=False)

    cy = panels["country_year"]
    print(f"country-year rows: {len(cy):,}")
    print(f"total flow (all years): {cy['flow_count'].sum():,}")
    print(f"years: {sorted(cy['year'].unique())}")
    print(f"distinct country pairs: {cy.groupby(['sending_code','receiving_code']).ngroups:,}")
    print("flow by year:")
    print(cy.groupby("year")["flow_count"].sum().to_string())
    print("\ntop 2023 destinations (receiving country):")
    latest = cy[cy["year"] == cy["year"].max()]
    print(latest.groupby("receiving_country")["flow_count"].sum().sort_values(ascending=False).head(10).to_string())
    print(f"\nLAU-year rows: {len(panels['lau_year']):,} | NUTS-year rows: {len(panels['nuts_year']):,}")


if __name__ == "__main__":
    main()
