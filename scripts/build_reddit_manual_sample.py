"""Stratified sample of Reddit destination mentions for manual sentiment validation.

Pulls ~51 mentions (17 positive, 17 neutral, 17 negative) from the LLM-extracted
`data/processed/reddit_destination_mentions.json`, joins each one back to the
raw post/comment text in `data/raw/reddit_raw.json`, and writes an xlsx with
the LLM label alongside empty `manual_*` columns for hand-labelling.

Used to compute LLM-vs-human agreement for the report's text-as-data section
(course requirement: manual evaluation on a small labeled sample).
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/reddit_raw.json")
LABELS = Path("data/processed/reddit_destination_mentions.json")
OUT = Path("data/processed/reddit_manual_validation.xlsx")

SEED = 42
PER_CLASS = 17
TEXT_LIMIT = 1500


def load_text_lookup() -> dict[tuple[str, str], dict]:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    return {(r["kind"], r["id"]): r for r in raw}


def build_rows() -> pd.DataFrame:
    text_lookup = load_text_lookup()
    extractions = json.loads(LABELS.read_text(encoding="utf-8"))

    rows: list[dict] = []
    for rec in extractions:
        src = text_lookup.get((rec["kind"], rec["id"]), {})
        title = (src.get("title") or "").strip()
        body = (src.get("text") or "").strip()
        for idx, m in enumerate(rec.get("mentions", [])):
            rows.append({
                "source_id": rec["id"],
                "kind": rec["kind"],
                "mention_idx": idx,
                "permalink": rec["permalink"],
                "city": m.get("city"),
                "country": m.get("country"),
                "llm_sentiment": m.get("sentiment"),
                "llm_sentiment_score": m.get("sentiment_score"),
                "llm_confidence": m.get("confidence"),
                "themes": "; ".join(m.get("themes", [])),
                "source_title": title,
                "source_text": body[:TEXT_LIMIT],
            })
    return pd.DataFrame(rows)


def stratified_sample(df: pd.DataFrame) -> pd.DataFrame:
    rng = random.Random(SEED)
    parts = []
    for label in ("positive", "neutral", "negative"):
        pool = df[df["llm_sentiment"] == label]
        n = min(PER_CLASS, len(pool))
        idx = rng.sample(list(pool.index), n)
        parts.append(pool.loc[idx])
    sample = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)
    sample["manual_sentiment"] = ""
    sample["manual_themes_ok"] = ""
    sample["manual_notes"] = ""
    return sample


def main() -> None:
    df = build_rows()
    sample = stratified_sample(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "source_id", "kind", "mention_idx", "permalink",
        "city", "country",
        "llm_sentiment", "llm_sentiment_score", "llm_confidence", "themes",
        "manual_sentiment", "manual_themes_ok", "manual_notes",
        "source_title", "source_text",
    ]
    sample = sample[cols]
    sample.to_excel(OUT, index=False, sheet_name="validation")
    print(f"wrote {len(sample)} rows -> {OUT}")
    print(sample["llm_sentiment"].value_counts().to_string())


if __name__ == "__main__":
    main()
