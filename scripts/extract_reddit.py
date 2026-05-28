import argparse
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from unilife.reddit import RAW_REDDIT
from unilife.reddit_extract import extract_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM extraction of Erasmus destination mentions.")
    parser.add_argument("--limit", type=int, default=100, help="Max records to process (highest score first).")
    parser.add_argument("--all", action="store_true", help="Process all usable records (ignores --limit).")
    args = parser.parse_args()

    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    records = json.loads(RAW_REDDIT.read_text(encoding="utf-8"))
    results = extract_corpus(records, limit=None if args.all else args.limit)

    (output_dir / "reddit_destination_mentions.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rows = []
    for r in results:
        for m in r["mentions"]:
            rows.append(
                {
                    "source_id": r["id"],
                    "kind": r["kind"],
                    "score": r["score"],
                    "permalink": r["permalink"],
                    "city": m.get("city"),
                    "country": m.get("country"),
                    "sentiment": m.get("sentiment"),
                    "themes": "; ".join(m.get("themes", [])),
                    "confidence": m.get("confidence"),
                }
            )
    flat = pd.DataFrame(rows)
    flat.to_csv(output_dir / "reddit_destination_mentions.csv", index=False)

    errors = sum(1 for r in results if "error" in r)
    print(f"records processed: {len(results):,} (errors: {errors})")
    print(f"mentions extracted: {len(flat):,}")
    if not flat.empty:
        print("top countries:")
        print(flat["country"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
