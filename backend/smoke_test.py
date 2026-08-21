"""
smoke_test.py
-------------
End-to-end smoke test for all three Phase 2 endpoints.
Run while the uvicorn dev server is active on port 8000.

Usage:
    python smoke_test.py
"""

import sys
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
PASS = "[PASS]"
FAIL = "[FAIL]"
all_ok = True


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def check(label: str, condition: bool, detail: str = "") -> None:
    global all_ok
    icon = PASS if condition else FAIL
    print(f"  {icon}  {label}" + (f"  ({detail})" if detail else ""))
    if not condition:
        all_ok = False


print("\n=== Smoke Test: Phase 2 Endpoints ===\n")

# ── 1. Health check ──────────────────────────────────────────────────────────
print("1. GET /")
status, body = request("GET", "/")
check("status 200", status == 200, f"got {status}")
check('body == {"status": "ok"}', body == {"status": "ok"}, str(body))

# ── 2. POST /api/suggest-tags — happy path ───────────────────────────────────
print("\n2. POST /api/suggest-tags (valid input)")
status, body = request("POST", "/api/suggest-tags", {
    "title": "How we built our LLM-powered backend in a weekend",
    "body": "We used FastAPI, Supabase, and Groq to build a fully functional tagging service.",
})
check("status 200", status == 200, f"got {status}")
check("has post_id", "post_id" in body, str(body))
check("has suggestion_id", "suggestion_id" in body)
check("has was_fallback", "was_fallback" in body, str(body))
check("suggested_tags is list", isinstance(body.get("suggested_tags"), list))
check("1-3 tags returned", 1 <= len(body.get("suggested_tags", [])) <= 3,
      str(body.get("suggested_tags")))
post_id = body.get("post_id")
suggestion_id = body.get("suggestion_id")
suggested_tags = body.get("suggested_tags", [])
was_fallback = body.get("was_fallback")
print(f"     suggested_tags = {suggested_tags}, was_fallback = {was_fallback}")

# ── 3. POST /api/suggest-tags — blank title -> 422 ────────────────────────────
print("\n3. POST /api/suggest-tags (blank title -> 422)")
status, body = request("POST", "/api/suggest-tags", {"title": "   ", "body": "some body"})
check("status 422", status == 422, f"got {status}")

# ── 4. POST /api/confirm-tags — happy path ───────────────────────────────────
print("\n4. POST /api/confirm-tags (valid correction)")
final_tags = suggested_tags  # confirm as-is (was_correct should be True)
status, body = request("POST", "/api/confirm-tags", {
    "suggestion_id": suggestion_id,
    "final_tags": final_tags,
})
check("status 200", status == 200, f"got {status}")
check("has correction_id", "correction_id" in body)
check("was_correct is True (tags unchanged)", body.get("was_correct") is True,
      str(body))
correction_id = body.get("correction_id")
print(f"     correction = {body}")

# ── 5. POST /api/confirm-tags — duplicate -> 409 ──────────────────────────────
print("\n5. POST /api/confirm-tags (duplicate -> 409)")
status, body = request("POST", "/api/confirm-tags", {
    "suggestion_id": suggestion_id,
    "final_tags": final_tags,
})
check("status 409", status == 409, f"got {status}")
print(f"     detail = {body.get('detail')}")

# ── 6. POST /api/confirm-tags — invalid tag -> 422 ────────────────────────────
print("\n6. POST /api/suggest-tags -> confirm with out-of-taxonomy tag -> 422")
status, body2 = request("POST", "/api/suggest-tags", {
    "title": "Another post for tag validation test",
    "body": "Just testing that bad tags are rejected.",
})
if status == 200:
    sid2 = body2["suggestion_id"]
    status, body = request("POST", "/api/confirm-tags", {
        "suggestion_id": sid2,
        "final_tags": ["NotARealTag"],
    })
    check("status 422 for invalid tag", status == 422, f"got {status}")
else:
    check("could not create second post for test", False, str(body2))

# ── 7. POST /api/suggest-tags & /api/confirm-tags — tag substitution ─────────
print("\n7. POST /api/suggest-tags -> confirm with tag substitution")
status, body_sub = request("POST", "/api/suggest-tags", {
    "title": "Machine learning research paper on neural network performance",
    "body": "Analyzing transformers and deep learning models for classification.",
})
check("status 200 for suggestion creation", status == 200, f"got {status}")
sub_suggestion_id = body_sub.get("suggestion_id")
sub_suggested_tags = body_sub.get("suggested_tags", [])
from_tag = sub_suggested_tags[0] if sub_suggested_tags else "General"
to_tag = "AI/ML" if from_tag != "AI/ML" else "Design"

status, body_confirm = request("POST", "/api/confirm-tags", {
    "suggestion_id": sub_suggestion_id,
    "final_tags": [to_tag],
})
check("status 200 for tag substitution", status == 200, f"got {status}")
check("was_correct is False", body_confirm.get("was_correct") is False, str(body_confirm))
check("tags_removed contains from_tag", from_tag in body_confirm.get("tags_removed", []), str(body_confirm))
check("tags_added contains to_tag", to_tag in body_confirm.get("tags_added", []), str(body_confirm))
print(f"     substitution recorded: {from_tag} -> {to_tag}")

# ── 8. GET /api/metrics ───────────────────────────────────────────────────────
print("\n8. GET /api/metrics")
status, body = request("GET", "/api/metrics")
check("status 200", status == 200, f"got {status}")
check("has total_suggestions", "total_suggestions" in body, str(body))
check("has total_corrections", "total_corrections" in body)
check("has agreement_rate", "agreement_rate" in body)
check("has per_tag_stats", "per_tag_stats" in body, str(body))
check("has tag_substitution_patterns", "tag_substitution_patterns" in body, str(body))
check("total_suggestions >= 1", body.get("total_suggestions", 0) >= 1,
      str(body.get("total_suggestions")))
check("total_corrections >= 1", body.get("total_corrections", 0) >= 1,
      str(body.get("total_corrections")))
check("agreement_rate 0.0-1.0",
      0.0 <= body.get("agreement_rate", -1) <= 1.0,
      str(body.get("agreement_rate")))

per_tag_stats = body.get("per_tag_stats", {})
check("per_tag_stats has 8 taxonomy tags", len(per_tag_stats) == 8, f"got {len(per_tag_stats)}")
sample_tag_ok = True
for tag, stats in per_tag_stats.items():
    if "times_suggested" not in stats or "times_survived" not in stats:
        sample_tag_ok = False
        break
check("per_tag_stats structure valid", sample_tag_ok, str(per_tag_stats))

sub_patterns = body.get("tag_substitution_patterns", [])
check("tag_substitution_patterns is list", isinstance(sub_patterns, list), str(sub_patterns))

found_pattern = False
for pat in sub_patterns:
    if pat.get("from_tag") == from_tag and pat.get("to_tag") == to_tag and pat.get("count", 0) >= 1:
        found_pattern = True
        break
check(f"tag_substitution_patterns contains {{from_tag: {from_tag!r}, to_tag: {to_tag!r}, count >= 1}}",
      found_pattern, str(sub_patterns))

print(f"     metrics = {json.dumps(body, indent=2)}")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
if all_ok:
    print("[OK] All smoke tests passed.\n")
else:
    print("[FAIL] One or more smoke tests failed.\n")
    sys.exit(1)

