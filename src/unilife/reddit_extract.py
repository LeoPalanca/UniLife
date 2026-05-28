from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable, Literal

import requests
from pydantic import BaseModel, Field

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ENV_PATH = Path(".env")


class DestinationMention(BaseModel):
    city: str | None = None
    country: str
    sentiment: Literal["positive", "neutral", "negative"]
    themes: list[str] = Field(
        default_factory=list,
        description="Examples: cost, housing, nightlife, academics, safety, bureaucracy",
    )
    confidence: float = Field(ge=0.0, le=1.0)


class PostExtraction(BaseModel):
    mentions: list[DestinationMention] = Field(default_factory=list)


def load_api_key() -> str:
    """Read OPENROUTER_API_KEY from the environment or the local .env (whitespace-tolerant)."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY"):
                value = line[len("OPENROUTER_API_KEY"):].lstrip("=: ").strip()
                if value:
                    return value.strip("\"'")
    raise RuntimeError("OPENROUTER_API_KEY not set. Add it to .env or the environment.")


PROMPT = (
    "You extract structured information from a Reddit post or comment about the "
    "Erasmus exchange programme. Identify every distinct destination (a European "
    "city and/or country) the author talks about. For each, give the sentiment the "
    "author expresses toward it and the themes discussed (e.g. cost, housing, "
    "nightlife, academics, safety, bureaucracy, social life, weather). Only include "
    "destinations actually discussed, not passing geographic mentions.\n\n"
    "Return ONLY a JSON object of the form "
    '{"mentions": [{"city": str|null, "country": str, '
    '"sentiment": "positive"|"neutral"|"negative", "themes": [str], '
    '"confidence": number 0..1}]}. '
    "If no destination is discussed, return {\"mentions\": []}.\n\nTEXT:\n"
)


def _is_retryable(exc: Exception) -> bool:
    text = str(exc).lower()
    transient = ("429", "resource_exhausted", "503", "500", "502", "unavailable", "overloaded", "deadline", "timeout")
    return any(token in text for token in transient)


def extract_text(api_key: str, text: str, model: str = DEFAULT_MODEL, retries: int = 5) -> PostExtraction:
    """Run one structured extraction call against OpenRouter, backing off on transient errors."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://unilife.ellep.it",
        "X-Title": "UniLife Erasmus research",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT + text}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    for attempt in range(retries):
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=90)
            if response.status_code in (429, 500, 502, 503):
                raise RuntimeError(f"{response.status_code} {response.text[:200]}")
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return PostExtraction.model_validate_json(content)
        except Exception as exc:
            if _is_retryable(exc) and attempt < retries - 1:
                time.sleep(min(8 * (attempt + 1), 40))
                continue
            raise


def extract_corpus(
    records: list[dict],
    limit: int | None = 100,
    min_chars: int = 80,
    model: str = DEFAULT_MODEL,
    pause: float = 1.0,
    progress_every: int = 0,
    on_progress: Callable[[int, int, list[dict]], None] | None = None,
) -> list[dict]:
    """Extract destination mentions from the highest-signal records.

    Records are ranked by score so a bounded sample (``limit``) captures the most
    discussed destinations while keeping API cost predictable.
    """
    api_key = load_api_key()

    usable = [r for r in records if len((r.get("title", "") + " " + r.get("text", "")).strip()) >= min_chars]
    usable.sort(key=lambda r: r.get("score", 0), reverse=True)
    if limit is not None:
        usable = usable[:limit]

    results: list[dict] = []
    total = len(usable)
    for index, record in enumerate(usable, start=1):
        text = (record.get("title", "") + "\n" + record.get("text", "")).strip()
        try:
            extraction = extract_text(api_key, text, model=model)
            mentions = [m.model_dump() for m in extraction.mentions]
        except Exception as exc:  # keep going; record the failure for review
            mentions = []
            results.append(
                {"id": record["id"], "kind": record["kind"], "score": record.get("score", 0),
                 "permalink": record.get("permalink"), "error": str(exc), "mentions": []}
            )
            time.sleep(pause)
            if progress_every and (index % progress_every == 0 or index == total):
                print(f"processed {index:,}/{total:,} prompts", flush=True)
                if on_progress:
                    on_progress(index, total, results)
            continue
        results.append(
            {
                "id": record["id"],
                "kind": record["kind"],
                "score": record.get("score", 0),
                "permalink": record.get("permalink"),
                "mentions": mentions,
            }
        )
        time.sleep(pause)
        if progress_every and (index % progress_every == 0 or index == total):
            print(f"processed {index:,}/{total:,} prompts", flush=True)
            if on_progress:
                on_progress(index, total, results)
    return results
