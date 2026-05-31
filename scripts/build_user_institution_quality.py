"""Build a user-based city-level institution-quality score (beta3 cross-check).

StudyPortals (mastersportal.com) shows a *student* review score (out of 5, only
displayed once >=10 students rate) for each university, with its city + country
on the page. The live site is Cloudflare-gated, so pages are read from the
Internet Archive (Wayback), which serves the full archived HTML. The university
page list comes from the Wayback CDX index.

Parsed per page:
  score  : meta description "... overall score of N stars."  (student rating /5)
  city   : body "... located in City, Country ..."
Then snapped to our Erasmus destination cities; per (receiving_code, city_norm)
we keep the best (max) user score and the university count. This is the crowd
counterpart to the expert/metric QS score in build_institution_quality.py.

Cached to data/raw/studyportals_raw.csv so the scrape is resumable and reruns
are free. Cumulative score -> time-invariant (like QoL), so cross-section only.
"""
from __future__ import annotations

import re
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from erasmusgravity.db import read_table
from erasmusgravity.erasmusu import norm_city

CDX = ("http://web.archive.org/cdx/search/cdx?url=mastersportal.com/rankings-reviews*"
       "&output=text&fl=original,timestamp&filter=statuscode:200&collapse=urlkey&limit=200000")
RAW = Path("data/raw/studyportals_raw.csv")
OUT = Path("data/processed/user_institution_quality.csv")
UA = {"User-Agent": "erasmusgravity-research/1.0 (leo.palanca01@gmail.com)"}

PAGE_RE = re.compile(r"/rankings-reviews/(\d+)/([a-z0-9-]+)\.html")
SCORE_RE = re.compile(r"overall score of ([\d.]+) stars", re.I)
LOC_RE = re.compile(r"located in ([^,<]+?),\s*([A-Za-z .]+?)(?: and| in |\.|<)", re.I)


def page_list() -> pd.DataFrame:
    with urllib.request.urlopen(urllib.request.Request(CDX, headers=UA), timeout=60) as r:
        text = r.read().decode("utf-8", "ignore")
    best: dict[tuple[str, str], tuple[str, str]] = {}
    for line in text.splitlines():
        m = PAGE_RE.search(line)
        if not m:
            continue
        ts = line.split()[-1]
        key = (m.group(1), m.group(2))
        if key not in best or ts > best[key][0]:
            best[key] = (ts, line.split()[0])
    rows = [{"uid": k[0], "slug": k[1], "ts": v[0], "url": v[1]} for k, v in best.items()]
    return pd.DataFrame(rows).drop_duplicates("uid")


def fetch(ts: str, url: str) -> str | None:
    wb = f"http://web.archive.org/web/{ts}id_/{url}"
    try:
        with urllib.request.urlopen(urllib.request.Request(wb, headers=UA), timeout=40) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001 - best-effort, cached + resumable
        print(f"    ! {url}: {e}")
        return None


def parse(html: str) -> dict | None:
    s = SCORE_RE.search(html)
    if not s:
        return None  # no displayed student score (too few reviews)
    loc = LOC_RE.search(html)
    return {
        "score": float(s.group(1)),
        "city": loc.group(1).strip() if loc else None,
        "country": loc.group(2).strip() if loc else None,
    }


def scrape(pages: pd.DataFrame) -> pd.DataFrame:
    cache = pd.read_csv(RAW) if RAW.exists() else pd.DataFrame(columns=["uid", "slug", "score", "city", "country"])
    done = set(cache["uid"].astype(str))
    rows = cache.to_dict("records")
    todo = [r for r in pages.to_dict("records") if str(r["uid"]) not in done]
    print(f"scraping {len(todo)} pages ({len(done)} cached)")
    for i, p in enumerate(todo, 1):
        html = fetch(p["ts"], p["url"])
        rec = parse(html) if html else None
        rows.append({"uid": p["uid"], "slug": p["slug"],
                     "score": rec["score"] if rec else None,
                     "city": rec["city"] if rec else None,
                     "country": rec["country"] if rec else None})
        if i % 25 == 0:
            print(f"  {i}/{len(todo)}")
            pd.DataFrame(rows).to_csv(RAW, index=False)
        time.sleep(0.8)
    out = pd.DataFrame(rows)
    out.to_csv(RAW, index=False)
    return out


def to_city_quality(sp: pd.DataFrame) -> pd.DataFrame:
    sp = sp.dropna(subset=["score", "city", "country"]).copy()
    flows = read_table("ka1_he_studies_flows_with_indicators")
    name2code = (flows.dropna(subset=["receiving_country", "receiving_code"])
                 .assign(k=lambda d: d["receiving_country"].str.lower().str.strip())
                 .drop_duplicates("k").set_index("k")["receiving_code"].to_dict())
    sp["receiving_code"] = sp["country"].str.lower().str.strip().map(name2code)
    sp = sp.dropna(subset=["receiving_code"])
    sp["city_norm"] = sp["city"].map(norm_city)
    return sp.groupby(["receiving_code", "city_norm"], as_index=False).agg(
        n_user_unis=("score", "size"), best_user_score=("score", "max"),
        mean_user_score=("score", "mean"))


def main() -> None:
    pages = page_list()
    print(f"university pages in Wayback index: {len(pages)}")
    sp = scrape(pages)
    n_scored = sp["score"].notna().sum()
    print(f"pages with a student score: {n_scored}")
    agg = to_city_quality(sp)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUT, index=False)
    print(f"saved {len(agg)} city rows -> {OUT}")
    print(agg.sort_values("best_user_score", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
