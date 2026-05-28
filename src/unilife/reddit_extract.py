from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

DEFAULT_MODEL = "gemini-2.5-flash"
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
    """Read GEMINI_API_KEY from the environment or the local .env (whitespace-tolerant)."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY") and "=" in line:
                return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY not set. Add it to .env or the environment.")


PROMPT = (
    "You extract structured information from a Reddit post or comment about the "
    "Erasmus exchange programme. Identify every distinct destination (a European "
    "city and/or country) the author talks about. For each, give the sentiment the "
    "author expresses toward it and the themes discussed (e.g. cost, housing, "
    "nightlife, academics, safety, bureaucracy, social life, weather). Only include "
    "destinations actually discussed, not passing geographic mentions. If none, "
    "return an empty list.\n\nTEXT:\n"
)


def _is_retryable(exc: Exception) -> bool:
    text = str(exc).lower()
    transient = ("429", "resource_exhausted", "503", "500", "unavailable", "overloaded", "deadline")
    return any(token in text for token in transient)


def extract_text(client, text: str, model: str = DEFAULT_MODEL, retries: int = 5) -> PostExtraction:
    """Run one structured extraction call against Gemini, backing off on transient errors."""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=PROMPT + text,
                config={"response_mime_type": "application/json", "response_schema": PostExtraction},
            )
            parsed = getattr(response, "parsed", None)
            if isinstance(parsed, PostExtraction):
                return parsed
            return PostExtraction.model_validate_json(response.text)
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
    pause: float = 4.0,
) -> list[dict]:
    """Extract destination mentions from the highest-signal records.

    Records are ranked by score so a bounded sample (``limit``) captures the most
    discussed destinations while keeping API cost predictable.
    """
    from google import genai

    client = genai.Client(api_key=load_api_key())

    usable = [r for r in records if len((r.get("title", "") + " " + r.get("text", "")).strip()) >= min_chars]
    usable.sort(key=lambda r: r.get("score", 0), reverse=True)
    if limit is not None:
        usable = usable[:limit]

    results: list[dict] = []
    for record in usable:
        text = (record.get("title", "") + "\n" + record.get("text", "")).strip()
        try:
            extraction = extract_text(client, text, model=model)
            mentions = [m.model_dump() for m in extraction.mentions]
        except Exception as exc:  # keep going; record the failure for review
            mentions = []
            results.append(
                {"id": record["id"], "kind": record["kind"], "score": record.get("score", 0),
                 "permalink": record.get("permalink"), "error": str(exc), "mentions": []}
            )
            time.sleep(pause)
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
    return results
