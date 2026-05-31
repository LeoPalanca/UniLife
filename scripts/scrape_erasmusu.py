"""Scrape Erasmusu per-city ratings as a dense quality-of-life signal.

Only scrapes cities that appear as a receiving city in the Erasmus flow data,
matched by normalised name, to keep the crawl bounded and relevant.
"""
import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.erasmusu import city_slugs, fetch_city_rating, norm_city

CITY_FLOWS = Path("data/processed/erasmus_city_flows_long.csv")
OUTPUT = Path("data/processed/erasmusu_city_ratings.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Erasmusu city ratings.")
    parser.add_argument("--pause", type=float, default=0.6, help="Seconds between requests.")
    parser.add_argument("--progress-every", type=int, default=25)
    args = parser.parse_args()

    flow_cities = set(pd.read_csv(CITY_FLOWS)["receiving_city"].dropna().map(norm_city))
    slugs = city_slugs()
    targets = [(s, norm_city(s.replace("-", " "))) for s in slugs]
    targets = [(s, c) for s, c in targets if c in flow_cities]
    print(f"sitemap city slugs: {len(slugs)} | matched to flow cities: {len(targets)}", flush=True)

    rows = []
    for i, (slug, _city) in enumerate(targets, start=1):
        rec = fetch_city_rating(slug, pause=args.pause)
        if rec:
            rec["city_norm"] = norm_city(slug.replace("-", " "))
            rows.append(rec)
        if i % args.progress_every == 0 or i == len(targets):
            print(f"  {i}/{len(targets)} fetched, {len(rows)} with rating", flush=True)
            pd.DataFrame(rows).to_csv(OUTPUT, index=False)

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT, index=False)
    print(f"\nsaved {len(df)} city ratings to {OUTPUT}")
    if not df.empty:
        print(f"rating_10: mean {df['rating_10'].mean():.2f}  median opinions {df['n_opinions'].median()}")
        print(df.sort_values("n_opinions", ascending=False).head(8).to_string(index=False))


if __name__ == "__main__":
    main()
