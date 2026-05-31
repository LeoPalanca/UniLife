from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable, Literal

import requests
from pydantic import BaseModel, Field, field_validator

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ENV_PATH = Path(".env")


ALLOWED_THEMES = {
    "cost_of_living",
    "housing",
    "academics",
    "social_life",
    "nightlife",
    "safety",
    "bureaucracy",
    "transport",
    "food",
    "weather",
    "language_barrier",
    "job_opportunities",
    "healthcare",
    "culture",
    "other",
}


class DestinationMention(BaseModel):
    city: str | None = None
    country: str
    sentiment: Literal["positive", "neutral", "negative"]
    sentiment_score: float = Field(
        description="Valence intensity: -1.0 very negative, 0.0 neutral/mixed, +1.0 very positive. "
        "Sign must agree with the sentiment label."
    )
    themes: list[str] = Field(
        default_factory=list,
        description="Only values from ALLOWED_THEMES; use 'other' if none fit.",
    )
    confidence: float = Field(
        description="Certainty (0-1) that this destination is genuinely discussed AND its sentiment "
        "is correctly captured. <0.5 = ambiguous/passing mention, >0.8 = explicit and unambiguous."
    )

    @field_validator("themes", mode="before")
    @classmethod
    def _clean_themes(cls, v):
        if not isinstance(v, list):
            return []
        cleaned = []
        for t in v:
            key = str(t).strip().lower().replace(" ", "_").replace("-", "_")
            cleaned.append(key if key in ALLOWED_THEMES else "other")
        return cleaned

    @field_validator("sentiment_score", mode="before")
    @classmethod
    def _clamp_score(cls, v):
        try:
            return max(-1.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return 0.0

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_conf(cls, v):
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return 0.5


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
    "city and/or country) the author actually discusses; ignore passing geographic "
    "mentions. For each destination report:\n"
    "- sentiment: the author's overall attitude, one of positive | neutral | negative.\n"
    "- sentiment_score: a number from -1.0 (very negative) through 0.0 (neutral/mixed) "
    "to +1.0 (very positive); its sign must match the sentiment label.\n"
    "- themes: zero or more of EXACTLY these values: cost_of_living, housing, academics, "
    "social_life, nightlife, safety, bureaucracy, transport, food, weather, language_barrier, "
    "job_opportunities, healthcare, culture, other. Use 'other' only if nothing fits.\n"
    "- confidence: a number 0..1 = how certain you are that the destination is genuinely "
    "discussed AND its sentiment is correctly captured. Use below 0.5 for ambiguous or "
    "passing mentions, above 0.8 only when explicit and unambiguous.\n"
    "If the author compares destinations, emit one mention per destination with its own "
    "sentiment.\n\n"
    "Return ONLY a JSON object of the form "
    '{"mentions": [{"city": str|null, "country": str, '
    '"sentiment": "positive"|"neutral"|"negative", "sentiment_score": number -1..1, '
    '"themes": [str], "confidence": number 0..1}]}. '
    'If no destination is discussed, return {"mentions": []}.\n\nTEXT:\n'
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
        "X-Title": "ErasmusGravity research",
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
                 "permalink": record.get("permalink"),
                 "created_utc": record.get("created_utc"),
                 "error": str(exc), "mentions": []}
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
                "created_utc": record.get("created_utc"),
                "mentions": mentions,
            }
        )
        time.sleep(pause)
        if progress_every and (index % progress_every == 0 or index == total):
            print(f"processed {index:,}/{total:,} prompts", flush=True)
            if on_progress:
                on_progress(index, total, results)
    return results
