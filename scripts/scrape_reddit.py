import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.reddit import RAW_REDDIT, build_reddit_corpus


def main() -> None:
    RAW_REDDIT.parent.mkdir(parents=True, exist_ok=True)
    prior_n = 0
    if RAW_REDDIT.exists():
        try:
            prior_n = len(json.loads(RAW_REDDIT.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            prior_n = 0

    corpus = build_reddit_corpus()
    RAW_REDDIT.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")

    posts = sum(1 for row in corpus if row["kind"] == "post")
    comments = sum(1 for row in corpus if row["kind"] == "comment")
    delta = len(corpus) - prior_n
    print(f"records: {len(corpus):,} (posts: {posts:,}, comments: {comments:,}; Δ vs prior: {delta:+,})")
    print(f"saved: {RAW_REDDIT}")


if __name__ == "__main__":
    main()
