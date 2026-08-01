"""
main.py
-------
FastAPI application entry point.

Endpoints
---------
GET  /                       Health check
POST /api/suggest-tags       Create a post and return Groq tag suggestions
POST /api/confirm-tags       Record a human correction for a suggestion
GET  /api/metrics            Return agreement metrics across all corrections

Session pattern
---------------
Uses database.py's get_session_local() (lazy engine).  Every request handler
receives a SQLAlchemy Session via the `get_db` FastAPI dependency; the session
is always closed in the finally block regardless of success or error.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from classifier import suggest_tags
from database import get_session_local
from models import HumanCorrection, ModelSuggestion, Post
from taxonomy import TAG_TAXONOMY

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------

app = FastAPI(title="Auto-Tagging Pipeline", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # CRA dev server
        "https://auto-tagging-pipeline-with-feedback.vercel.app",  # Production Vercel app
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SuggestTagsRequest(BaseModel):
    title: str
    body: str

    @field_validator("title", "body")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace-only")
        return v.strip()


class SuggestTagsResponse(BaseModel):
    post_id: str
    suggestion_id: str
    suggested_tags: list[str]
    was_fallback: bool


class ConfirmTagsRequest(BaseModel):
    suggestion_id: str
    final_tags: list[str]

    @field_validator("final_tags")
    @classmethod
    def validate_tags(cls, tags: list[str]) -> list[str]:
        if not tags:
            raise ValueError("final_tags must contain at least one tag")
        taxonomy_set = set(TAG_TAXONOMY)
        invalid = [t for t in tags if t not in taxonomy_set]
        if invalid:
            raise ValueError(
                f"Tags not in taxonomy: {invalid}. "
                f"Allowed values: {TAG_TAXONOMY}"
            )
        if len(tags) > 3:
            raise ValueError("final_tags may contain at most 3 tags")
        # deduplicate, preserve order
        seen: set[str] = set()
        deduped: list[str] = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        return deduped


class ConfirmTagsResponse(BaseModel):
    correction_id: str
    was_correct: bool
    tags_added: list[str]
    tags_removed: list[str]


class DailyTrendEntry(BaseModel):
    date: str                  # ISO date string "YYYY-MM-DD"
    suggestions: int          # count of model_suggestions created on that day
    corrections: int          # count of human_corrections created on that day
    agreement_rate: float     # was_correct=True / corrections on that day, 0.0 if 0 corrections


class PerTagStat(BaseModel):
    times_suggested: int
    times_survived: int


class MetricsResponse(BaseModel):
    total_suggestions: int
    total_corrections: int
    agreement_rate: float          # fraction of corrections where was_correct=True
    per_tag_stats: dict[str, PerTagStat]
    top_tags_added: list[str]      # most frequently added tags (descending)
    top_tags_removed: list[str]    # most frequently removed tags (descending)
    daily_trend: list[DailyTrendEntry]



# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok"}


@app.post("/api/suggest-tags", response_model=SuggestTagsResponse, tags=["tagging"])
def api_suggest_tags(payload: SuggestTagsRequest, db: Session = Depends(get_db)):
    """
    1. Validates that title and body are non-blank (422 otherwise).
    2. Persists a Post row.
    3. Calls the Groq classifier; on ANY failure falls back to ["General"]
       so the post is still created and a suggestion is still stored.
    4. Persists a ModelSuggestion row with was_fallback flag.
    5. Returns post_id, suggestion_id, suggested_tags, and was_fallback.
    """
    # --- Create Post --------------------------------------------------------
    post = Post(title=payload.title, body=payload.body)
    db.add(post)
    db.flush()   # get post.id before calling Groq

    # --- Call Groq (errors are caught inside suggest_tags) ------------------
    try:
        tags, was_fallback = suggest_tags(payload.title, payload.body)
    except Exception as exc:   # belt-and-suspenders: suggest_tags should never raise
        logger.warning("suggest_tags raised unexpectedly: %s", exc)
        tags, was_fallback = ["General"], True

    # --- Create ModelSuggestion ---------------------------------------------
    suggestion = ModelSuggestion(
        post_id=post.id,
        suggested_tags=tags,
        was_fallback=was_fallback,
    )
    db.add(suggestion)
    db.commit()
    db.refresh(post)
    db.refresh(suggestion)

    return SuggestTagsResponse(
        post_id=str(post.id),
        suggestion_id=str(suggestion.id),
        suggested_tags=suggestion.suggested_tags,
        was_fallback=suggestion.was_fallback,
    )


@app.post("/api/confirm-tags", response_model=ConfirmTagsResponse, tags=["tagging"])
def api_confirm_tags(payload: ConfirmTagsRequest, db: Session = Depends(get_db)):
    """
    Record a human correction for a model suggestion.

    - 404  if suggestion_id does not exist.
    - 409  if this suggestion already has a correction (UNIQUE constraint).
    - Precomputes was_correct, tags_added, tags_removed at write time.
    """
    import uuid as _uuid

    # --- Resolve suggestion -------------------------------------------------
    try:
        suggestion_uuid = _uuid.UUID(payload.suggestion_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="suggestion_id must be a valid UUID")

    suggestion: ModelSuggestion | None = db.get(ModelSuggestion, suggestion_uuid)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="suggestion not found")

    # --- Precompute diff fields ---------------------------------------------
    suggested_set = set(suggestion.suggested_tags)
    final_set = set(payload.final_tags)

    was_correct = suggested_set == final_set
    tags_added = sorted(final_set - suggested_set)
    tags_removed = sorted(suggested_set - final_set)

    # --- Persist (catches UNIQUE violation on suggestion_id) ----------------
    correction = HumanCorrection(
        post_id=suggestion.post_id,
        suggestion_id=suggestion.id,
        final_tags=payload.final_tags,
        was_correct=was_correct,
        tags_added=tags_added,
        tags_removed=tags_removed,
    )
    db.add(correction)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This suggestion has already been confirmed. "
                   "A suggestion can only be corrected once.",
        )

    db.refresh(correction)

    return ConfirmTagsResponse(
        correction_id=str(correction.id),
        was_correct=was_correct,
        tags_added=tags_added,
        tags_removed=tags_removed,
    )


@app.get("/api/metrics", response_model=MetricsResponse, tags=["metrics"])
def api_metrics(db: Session = Depends(get_db)):
    """
    Aggregate metrics across all human corrections and suggestions.

    Returns:
      - total_suggestions : int
      - total_corrections : int
      - agreement_rate    : float  (0.0–1.0; 0.0 if no corrections yet)
      - per_tag_stats     : dict[str, PerTagStat]
      - top_tags_added    : list[str]  ordered by frequency desc
      - top_tags_removed  : list[str]  ordered by frequency desc
      - daily_trend       : list[DailyTrendEntry] chronological entries
    """
    total_suggestions: int = db.scalar(select(func.count()).select_from(ModelSuggestion)) or 0
    total: int = db.scalar(select(func.count()).select_from(HumanCorrection)) or 0
    correct: int = (
        db.scalar(
            select(func.count()).select_from(HumanCorrection)
            .where(HumanCorrection.was_correct.is_(True))
        )
        or 0
    )
    agreement_rate = round(correct / total, 4) if total > 0 else 0.0

    # --- Per-tag stats ------------------------------------------------------
    suggested_rows = db.execute(
        select(
            func.unnest(ModelSuggestion.suggested_tags).label("tag"),
            func.count().label("n"),
        )
        .group_by("tag")
    ).all()
    suggested_counts = {row.tag: row.n for row in suggested_rows}

    survived_subquery = (
        select(
            func.unnest(HumanCorrection.final_tags).label("tag"),
            ModelSuggestion.suggested_tags.label("suggested_tags"),
        )
        .join(ModelSuggestion, HumanCorrection.suggestion_id == ModelSuggestion.id)
        .subquery()
    )
    survived_rows = db.execute(
        select(
            survived_subquery.c.tag,
            func.count().label("n"),
        )
        .where(survived_subquery.c.tag == func.any(survived_subquery.c.suggested_tags))
        .group_by(survived_subquery.c.tag)
    ).all()
    survived_counts = {row.tag: row.n for row in survived_rows}

    per_tag_stats = {
        tag: PerTagStat(
            times_suggested=suggested_counts.get(tag, 0),
            times_survived=survived_counts.get(tag, 0),
        )
        for tag in TAG_TAXONOMY
    }

    # --- Top added tags (UNNEST + GROUP BY + ORDER BY count desc) -----------
    added_rows = db.execute(
        select(
            func.unnest(HumanCorrection.tags_added).label("tag"),
            func.count().label("n"),
        )
        .group_by("tag")
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    top_tags_added = [row.tag for row in added_rows]

    # --- Top removed tags ---------------------------------------------------
    removed_rows = db.execute(
        select(
            func.unnest(HumanCorrection.tags_removed).label("tag"),
            func.count().label("n"),
        )
        .group_by("tag")
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    top_tags_removed = [row.tag for row in removed_rows]

    # --- Daily trend over time ----------------------------------------------
    sug_date_col = func.to_char(ModelSuggestion.created_at, "YYYY-MM-DD").label("date_str")
    sug_by_day_rows = db.execute(
        select(
            sug_date_col,
            func.count().label("n"),
        )
        .group_by("date_str")
    ).all()
    sug_by_day = {row.date_str: row.n for row in sug_by_day_rows if row.date_str}

    corr_date_col = func.to_char(HumanCorrection.created_at, "YYYY-MM-DD").label("date_str")
    corr_by_day_rows = db.execute(
        select(
            corr_date_col,
            func.count().label("n_total"),
            func.sum(case((HumanCorrection.was_correct.is_(True), 1), else_=0)).label("n_correct"),
        )
        .group_by("date_str")
    ).all()
    corr_by_day = {
        row.date_str: (row.n_total, int(row.n_correct or 0))
        for row in corr_by_day_rows
        if row.date_str
    }

    all_dates = sorted(set(sug_by_day.keys()).union(set(corr_by_day.keys())))

    daily_trend: list[DailyTrendEntry] = []
    for d_str in all_dates:
        s_count = sug_by_day.get(d_str, 0)
        c_total, c_correct = corr_by_day.get(d_str, (0, 0))
        if s_count == 0 and c_total == 0:
            continue
        day_agreement = round(c_correct / c_total, 4) if c_total > 0 else 0.0
        daily_trend.append(
            DailyTrendEntry(
                date=d_str,
                suggestions=s_count,
                corrections=c_total,
                agreement_rate=day_agreement,
            )
        )

    return MetricsResponse(
        total_suggestions=total_suggestions,
        total_corrections=total,
        agreement_rate=agreement_rate,
        per_tag_stats=per_tag_stats,
        top_tags_added=top_tags_added,
        top_tags_removed=top_tags_removed,
        daily_trend=daily_trend,
    )
