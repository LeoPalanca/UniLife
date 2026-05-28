from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from unilife.geocode import build_city_coordinates


def main() -> None:
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    coords = build_city_coordinates()
    coords.to_csv(output_dir / "city_coordinates.csv", index=False)

    total = coords["inbound_flow"].sum()
    by_level = coords.groupby("match_level")["inbound_flow"].sum() / total * 100
    print(f"receiving cities: {len(coords):,}")
    print("flow-weighted match level (%):")
    print(by_level.round(1).to_string())


if __name__ == "__main__":
    main()
