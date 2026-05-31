import argparse
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.reddit import RAW_REDDIT
from erasmusgravity.reddit_extract import DEFAULT_MODEL, extract_corpus


OUTPUT_DIR = Path("data/processed")
OUTPUT_JSON = OUTPUT_DIR / "reddit_destination_mentions.json"
OUTPUT_CSV = OUTPUT_DIR / "reddit_destination_mentions.csv"


def flatten_results(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        for m in r["mentions"]:
            rows.append(
                {
                    "source_id": r["id"],
                    "kind": r["kind"],
                    "score": r["score"],
                    "permalink": r["permalink"],
                    "created_utc": r.get("created_utc"),
                    "city": m.get("city"),
                    "country": m.get("country"),
                    "sentiment": m.get("sentiment"),
                    "sentiment_score": m.get("sentiment_score"),
                    "themes": "; ".join(m.get("themes", [])),
                    "confidence": m.get("confidence"),
                }
            )
    return pd.DataFrame(rows)


def write_outputs(results: list[dict]) -> pd.DataFrame:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    flat = flatten_results(results)
    flat.to_csv(OUTPUT_CSV, index=False)
    return flat


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM extraction of Erasmus destination mentions.")
    parser.add_argument("--limit", type=int, default=100, help="Max records to process (highest score first).")
    parser.add_argument("--all", action="store_true", help="Process all usable records (ignores --limit).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model slug.")
    parser.add_argument("--pause", type=float, default=1.0, help="Seconds to wait between API calls.")
    parser.add_argument("--resume", action="store_true", help="Skip records already present in the output JSON.")
    parser.add_argument("--progress-every", type=int, default=10, help="Print and checkpoint every N prompts.")
    parser.add_argument(
        "--productive-from",
        help="Prior results JSON; only re-process records that had a mention or errored "
        "(skips records previously found empty to save API calls).",
    )
    args = parser.parse_args()

    records = json.loads(RAW_REDDIT.read_text(encoding="utf-8"))

    if args.productive_from:
        prior = json.loads(Path(args.productive_from).read_text(encoding="utf-8"))
        keep = {(r.get("kind"), r.get("id")) for r in prior if r.get("mentions") or "error" in r}
        before = len(records)
        records = [r for r in records if (r.get("kind"), r.get("id")) in keep]
        print(f"productive filter: {len(records):,} of {before:,} records (skipped previously-empty)", flush=True)

    existing: list[dict] = []
    if args.resume and OUTPUT_JSON.exists():
        existing = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        processed = {(r.get("kind"), r.get("id")) for r in existing}
        records = [r for r in records if (r.get("kind"), r.get("id")) not in processed]
        print(f"resume: keeping {len(existing):,} existing records, {len(records):,} raw records left", flush=True)

    def checkpoint(_done: int, _total: int, partial: list[dict]) -> None:
        write_outputs(existing + partial)

    results = extract_corpus(
        records,
        limit=None if args.all else args.limit,
        model=args.model,
        pause=args.pause,
        progress_every=args.progress_every,
        on_progress=checkpoint if args.resume else None,
    )

    results = existing + results
    flat = write_outputs(results)

    errors = sum(1 for r in results if "error" in r)
    print(f"records processed: {len(results):,} (errors: {errors})")
    print(f"mentions extracted: {len(flat):,}")
    if not flat.empty:
        print("top countries:")
        print(flat["country"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
