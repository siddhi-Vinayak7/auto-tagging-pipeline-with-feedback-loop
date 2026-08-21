# Database Schema Reference

## Overview

Three tables capture the full lifecycle of a tag-suggestion interaction:

```
posts  ──(1:N)──►  model_suggestions  ──(1:1)──►  human_corrections
```

A **post** is submitted, the model generates **model_suggestions** (up to 3 tags), and the user may accept or edit those suggestions, creating a **human_correction** record.

---

## Tables

### `posts`

Stores the raw content submitted for tagging.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | `uuid` | PK, default `gen_random_uuid()` | Unique identifier for the post |
| `title` | `text` | NOT NULL | Short title of the post |
| `body` | `text` | NOT NULL | Full body content of the post |
| `created_at` | `timestamptz` | NOT NULL, default `now()` | When the post was submitted |

---

### `model_suggestions`

Stores the tag suggestions produced by the ML model for a given post.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | `uuid` | PK, default `gen_random_uuid()` | Unique identifier for this suggestion set |
| `post_id` | `uuid` | NOT NULL, FK → `posts.id` | Which post these suggestions belong to |
| `suggested_tags` | `text[]` | NOT NULL, max 3 items (app-enforced) | The tags the model suggested |
| `was_fallback` | `boolean` | NOT NULL, default `false` | `true` if the model call failed or timed out and fell back to default tags |
| `created_at` | `timestamptz` | NOT NULL, default `now()` | When suggestions were generated |

**Note:** The 3-tag maximum is enforced at the application layer (not a DB constraint) so the constraint is visible in code and can be changed without a schema migration.

---

### `human_corrections`

Stores the human's final tag decision alongside precomputed diff fields for fast metrics queries.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | `uuid` | PK, default `gen_random_uuid()` | Unique identifier for this correction |
| `post_id` | `uuid` | NOT NULL, FK → `posts.id` | Which post was corrected |
| `suggestion_id` | `uuid` | NOT NULL, FK → `model_suggestions.id`, **UNIQUE** | Which suggestion was being responded to — unique enforces one correction per suggestion |
| `final_tags` | `text[]` | NOT NULL | The tags the human settled on |
| `was_correct` | `boolean` | NOT NULL | `true` if `set(final_tags) == set(suggested_tags)` |
| `tags_added` | `text[]` | NOT NULL | `set(final_tags) - set(suggested_tags)` |
| `tags_removed` | `text[]` | NOT NULL | `set(suggested_tags) - set(final_tags)` |
| `created_at` | `timestamptz` | NOT NULL, default `now()` | When the correction was submitted |

---

## Relationships

```
posts.id  ◄──────────────────────────── model_suggestions.post_id
posts.id  ◄──────────────────────────── human_corrections.post_id
model_suggestions.id  ◄─────────────── human_corrections.suggestion_id
```

- One post can have **multiple** suggestion sets (e.g. if regenerated).
- One suggestion set can have **exactly one** human correction — enforced by `uq_human_corrections_suggestion_id` at the database level.
- `post_id` is denormalized onto `human_corrections` for simpler JOIN-free queries on the metrics endpoint.

---

## Why `was_correct`, `tags_added`, and `tags_removed` Are Precomputed

These three fields are derived values — they could be recomputed from `suggested_tags` and `final_tags` at query time. They are stored instead for these reasons:

1. **`/api/metrics` stays simple and fast.** Calculating set-differences across thousands of rows in a SQL query requires either complex `ARRAY` operations or fetching raw arrays into the application for processing. Both add latency and complexity. A stored `was_correct` boolean lets the metrics endpoint use `COUNT(*) WHERE was_correct = true` — a single indexed column scan.

2. **Aggregation is trivially efficient.** `tags_added` and `tags_removed` can be `UNNEST`-ed and `GROUP BY`-ed directly in SQL to produce "most commonly added tags" or "most commonly removed tags" — extremely useful for model improvement signals — without any application-layer post-processing.

3. **Auditability.** If the definition of "correct" ever changes (e.g. partial credit), the raw `suggested_tags` and `final_tags` are always available to backfill. The precomputed fields are a performance optimization, not the source of truth.

4. **Write-time cost is negligible.** The set operations happen exactly once per correction write, at a moment where the caller is already waiting for an HTTP response. This is far cheaper than recalculating on every read of the metrics dashboard.

5. **Chronological Daily Trends.** Stored timestamps (`created_at`) allow `GET /api/metrics` to group suggestions, corrections, and agreement rates by `DATE(created_at)` into a `daily_trend` array for tracking model performance over time.

6. **Tag Substitution Tracking.** When a correction has exactly one tag removed and exactly one tag added (`len(tags_removed) == 1 and len(tags_added) == 1`), `GET /api/metrics` records the 1-to-1 substitution pair in `tag_substitution_patterns` (e.g. `[{"from_tag": "LLM", "to_tag": "AI", "count": 4}, {"from_tag": "Frontend", "to_tag": "Design", "count": 1}]`) sorted by frequency descending. Multi-tag corrections (0 or 2+ tags removed/added) are excluded from substitution patterns to avoid Cartesian-product mapping ambiguities.

---

## Indexes & Constraints

Added in migrations `fbdce510ef7e` and `e2654160a1a8` (`add_was_fallback_to_model_suggestions`) on top of the initial schema `f9c935596961`.

### Unique Constraint

| Name | Table | Column | Purpose |
|------|-------|--------|---------|
| `uq_human_corrections_suggestion_id` | `human_corrections` | `suggestion_id` | Guarantees exactly one correction row per suggestion. Without this, a duplicated or retried `/corrections` request would insert a second row, inflating the total count in `agreement_rate` without a corresponding `was_correct=true`, silently biasing every metric downward. PostgreSQL automatically creates a unique index to back this constraint — no separate `CREATE INDEX` needed. |

### Indexes

| Name | Table | Column | Type | Purpose |
|------|-------|--------|------|---------|
| `ix_model_suggestions_post_id` | `model_suggestions` | `post_id` | Non-unique B-tree | All suggestion lookups and `/api/metrics` aggregations filter by `post_id`. Without an index, Postgres performs a full sequential scan; with it, the scan is O(log n). |
| `ix_human_corrections_post_id` | `human_corrections` | `post_id` | Non-unique B-tree | Same reasoning — post-scoped correction lookups and the JOIN inside the metrics aggregation use this column. |
| *(implicit)* `uq_human_corrections_suggestion_id` | `human_corrections` | `suggestion_id` | Unique B-tree | Created automatically by the unique constraint above. Doubles as a fast lookup index for correction-by-suggestion-id queries. |

---

## Tag Taxonomy

The fixed tag taxonomy is defined as a Python constant in [`backend/taxonomy.py`](../backend/taxonomy.py):

```python
TAG_TAXONOMY: list[str] = [
    "AI/ML",
    "Frontend",
    "Backend",
    "Product",
    "Design",
    "Career",
    "Funding",
    "General",
]
```

**Why a Python constant and not a database table?**

- The taxonomy is small (8 values) and changes only via a code deploy, not user action.
- Fetching it from a DB on every request would add a network round-trip for no benefit.
- Keeping it in code means it is version-controlled alongside the validation logic that uses it.
- If the taxonomy needs to grow significantly or become user-configurable in the future, migrating it to a DB table is straightforward.
