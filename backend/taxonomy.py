"""
taxonomy.py
-----------
Fixed tag taxonomy shared across the backend.

This is a Python constant — not a database table — because the tag list is
small, changes only via a code deploy, and having it in-process avoids an
extra round-trip on every tag-suggestion call.
"""

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
