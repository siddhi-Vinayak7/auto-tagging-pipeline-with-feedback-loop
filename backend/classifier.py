"""
classifier.py
-------------
Groq-powered tag suggestion.

Public API:
    suggest_tags(title, body) -> list[str]

Behaviour guarantees (regardless of what the model returns):
  - Output always contains 1–3 items.
  - Every item is a member of TAG_TAXONOMY.
  - Items are deduplicated.
  - On ANY failure (network error, timeout, bad JSON, out-of-taxonomy tags,
    empty list) the function falls back to ["General"] and logs a warning.
    It never raises an unhandled exception.
"""

import json
import logging
import os

from dotenv import load_dotenv
from groq import Groq

from taxonomy import TAG_TAXONOMY

load_dotenv()

logger = logging.getLogger(__name__)

_client: Groq | None = None

_TAXONOMY_STR = json.dumps(TAG_TAXONOMY)

_SYSTEM_PROMPT = f"""You are a content tagger. Your only job is to assign topic tags to a post.

Rules (you must follow ALL of them):
1. Choose between 1 and 3 tags (inclusive).
2. You may ONLY use tags from this exact list: {_TAXONOMY_STR}
3. Your entire response must be a single JSON array of strings — nothing else.
   No explanation, no markdown, no code block fences, no surrounding text.
4. Example of a valid response: ["AI/ML", "Backend"]
5. If no tag fits well, respond with: ["General"]
"""


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Add it to backend/.env before making tag-suggestion calls."
            )
        _client = Groq(api_key=api_key)
    return _client


def suggest_tags(title: str, body: str) -> tuple[list[str], bool]:
    """
    Call the Groq API to suggest 1–3 tags for a post.

    Parameters
    ----------
    title : str   Short title of the post.
    body  : str   Full body of the post.

    Returns
    -------
    tuple[list[str], bool]
        (1–3 tags, was_fallback flag).
        Falls back to (["General"], True) on any failure.
    """
    taxonomy_set = set(TAG_TAXONOMY)
    fallback = (["General"], True)

    try:
        client = _get_client()
        user_content = f"Title: {title}\n\nBody:\n{body}"

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,       # deterministic output
            max_tokens=64,         # JSON array of ≤3 short strings needs at most ~40 tokens
            timeout=8.0,           # fail fast — don't block the HTTP response
        )

        raw = response.choices[0].message.content.strip()

        # --- Defensive parse ------------------------------------------------
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("classifier: invalid JSON from Groq — raw=%r", raw)
            return fallback

        if not isinstance(parsed, list):
            logger.warning("classifier: expected list, got %s — raw=%r", type(parsed).__name__, raw)
            return fallback

        if len(parsed) == 0:
            logger.warning("classifier: model returned empty list — falling back")
            return fallback

        # Filter to only valid taxonomy members, deduplicate, preserve order
        valid_tags: list[str] = []
        seen: set[str] = set()
        invalid: list[str] = []
        for tag in parsed:
            if not isinstance(tag, str):
                invalid.append(repr(tag))
                continue
            if tag not in taxonomy_set:
                invalid.append(tag)
                continue
            if tag in seen:
                continue
            seen.add(tag)
            valid_tags.append(tag)

        if invalid:
            logger.warning("classifier: out-of-taxonomy or non-string tags removed: %s", invalid)

        if not valid_tags:
            logger.warning("classifier: no valid tags survived filtering — falling back")
            return fallback

        # Cap at 3
        return (valid_tags[:3], False)

    except Exception as exc:  # noqa: BLE001
        logger.warning("classifier: Groq call failed (%s: %s) — falling back to %s",
                       type(exc).__name__, exc, fallback)
        return fallback
