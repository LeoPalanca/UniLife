from __future__ import annotations

import json
import time
from pathlib import Path

import requests

USER_AGENT = "erasmusgravity/0.1 (Erasmus mobility study; contact: leo.palanca01@gmail.com)"
BASE = "https://www.reddit.com"
RAW_REDDIT = Path("data/raw/reddit_raw.json")


def _get(url: str, params: dict | None = None, pause: float = 2.5, retries: int = 5) -> dict | list:
    """GET a Reddit public JSON endpoint, backing off on throttling.

    Returns {} after exhausting retries instead of raising, so a single failed
    request does not abort a long crawl.
    """
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(retries):
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            time.sleep(pause)
            return response.json()
        if response.status_code in (429, 500, 502, 503):
            retry_after = response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else 20.0 * (attempt + 1)
            time.sleep(wait)
            continue
        response.raise_for_status()
    return {}


def fetch_posts(subreddit: str, sort: str = "top", t: str = "all", pages: int = 5) -> list[dict]:
    """Fetch posts from a subreddit listing, paginating with the 'after' token."""
    posts: list[dict] = []
    after: str | None = None
    for _ in range(pages):
        params = {"limit": 100, "t": t, "after": after} if after else {"limit": 100, "t": t}
        data = _get(f"{BASE}/r/{subreddit}/{sort}.json", params=params)
        children = data.get("data", {}).get("children", [])
        if not children:
            break
        for child in children:
            p = child["data"]
            posts.append(
                {
                    "kind": "post",
                    "id": p["id"],
                    "subreddit": p.get("subreddit"),
                    "title": p.get("title", ""),
                    "text": p.get("selftext", "") or "",
                    "score": p.get("score", 0),
                    "num_comments": p.get("num_comments", 0),
                    "created_utc": p.get("created_utc"),
                    "permalink": p.get("permalink"),
                }
            )
        after = data.get("data", {}).get("after")
        if not after:
            break
    return posts


def fetch_comments(subreddit: str, post_id: str, limit: int = 200) -> list[dict]:
    """Fetch top-level comments for a post (skips 'more' stubs)."""
    data = _get(f"{BASE}/r/{subreddit}/comments/{post_id}.json", params={"limit": limit})
    if not isinstance(data, list) or len(data) < 2:
        return []
    comments: list[dict] = []
    for child in data[1].get("data", {}).get("children", []):
        if child.get("kind") != "t1":
            continue
        c = child["data"]
        body = c.get("body", "") or ""
        if not body or body in ("[deleted]", "[removed]"):
            continue
        comments.append(
            {
                "kind": "comment",
                "id": c["id"],
                "link_id": post_id,
                "subreddit": c.get("subreddit"),
                "title": "",
                "text": body,
                "score": c.get("score", 0),
                "created_utc": c.get("created_utc"),
                "permalink": c.get("permalink"),
            }
        )
    return comments


def _key_for(row: dict) -> str:
    return f"c_{row['id']}" if row.get("kind") == "comment" else row["id"]


def build_reddit_corpus(
    subreddit: str = "Erasmus",
    comment_posts: int = 60,
    merge_existing: bool = True,
) -> list[dict]:
    """Collect a deduplicated corpus of posts plus comments for the busiest posts.

    When ``merge_existing`` and ``RAW_REDDIT`` exists, the prior snapshot is loaded
    first so re-runs accumulate coverage instead of overwriting it. For each id seen
    again we keep max(score) and max(num_comments) (Reddit votes only ratchet up
    meaningfully within the corpus's noise floor), preserve ``first_seen_utc``, and
    stamp ``last_seen_utc`` to the current run.
    """
    now = int(time.time())
    by_id: dict[str, dict] = {}

    if merge_existing and RAW_REDDIT.exists():
        try:
            for row in json.loads(RAW_REDDIT.read_text(encoding="utf-8")):
                by_id[_key_for(row)] = row
        except (json.JSONDecodeError, KeyError):
            by_id = {}

    def merge_in(new: dict) -> None:
        key = _key_for(new)
        prev = by_id.get(key)
        if prev:
            new["first_seen_utc"] = prev.get("first_seen_utc") or prev.get("created_utc")
            new["score"] = max(int(prev.get("score") or 0), int(new.get("score") or 0))
            if new.get("kind") == "post":
                new["num_comments"] = max(
                    int(prev.get("num_comments") or 0), int(new.get("num_comments") or 0)
                )
        else:
            new["first_seen_utc"] = new.get("created_utc")
        new["last_seen_utc"] = now
        by_id[key] = new

    listings = [("top", "all"), ("top", "year"), ("top", "month"), ("hot", "all"), ("new", "all")]
    fresh_post_ids: set[str] = set()
    for sort, t in listings:
        for post in fetch_posts(subreddit, sort=sort, t=t, pages=4):
            fresh_post_ids.add(post["id"])
            merge_in(post)

    fresh_posts = [by_id[pid] for pid in fresh_post_ids if pid in by_id]
    ranked = sorted(
        fresh_posts,
        key=lambda p: (int(p.get("num_comments") or 0), int(p.get("score") or 0)),
        reverse=True,
    )
    for post in ranked[:comment_posts]:
        try:
            for comment in fetch_comments(subreddit, post["id"]):
                merge_in(comment)
        except Exception:
            continue

    return list(by_id.values())
