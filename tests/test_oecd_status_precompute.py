"""
Tests for scripts/precompute_oecd_status.py.

All four tests use a mocked SPARQL result set — no network access required.
Monkeypatches fetch_aop_oecd_statuses() so build_oecd_status_index() runs
deterministically against in-memory data.
"""
from __future__ import annotations

import pytest

from scripts import precompute_oecd_status as oecd


# ---------------------------------------------------------------------------
# Fixture — mock SPARQL result set
# ---------------------------------------------------------------------------

MOCK_BINDINGS = [
    {
        "label": {"type": "literal", "value": "AOP 3"},
        "title": {"type": "literal", "value": "Inhibition of the mitochondrial complex I"},
        "status": {"type": "literal", "value": "WPHA/WNT Endorsed"},
    },
    {
        "label": {"type": "literal", "value": "AOP 1"},
        "title": {"type": "literal", "value": "Uncharacterized AOP with no status"},
        # no "status" key — simulates OPTIONAL not matching
    },
    {
        "label": {"type": "literal", "value": "AOP 999"},
        "title": {"type": "literal", "value": "Future AOP with novel status"},
        "status": {"type": "literal", "value": "Experimental Stage"},
    },
]


def _mock_fetch(endpoint=None):
    """Return a fixed raw dict keyed by AOP label."""
    raw = {}
    for row in MOCK_BINDINGS:
        label = row["label"]["value"]
        title = row["title"]["value"]
        status = row["status"]["value"] if "status" in row else None
        raw[label] = {"title": title, "status": status}
    return raw


# ---------------------------------------------------------------------------
# Test 1: Shape and "Unknown" fallback
# ---------------------------------------------------------------------------

def test_build_index_shape_and_unknown_fallback(monkeypatch):
    """
    Given a mocked SPARQL result (one AOP with status, one without),
    build_oecd_status_index() returns {"_meta": ..., "aops": ...};
    the AOP missing a status binding maps to "Unknown".
    """
    monkeypatch.setattr(oecd, "fetch_aop_oecd_statuses", _mock_fetch)

    result = oecd.build_oecd_status_index()

    assert "_meta" in result
    assert "aops" in result

    aops = result["aops"]
    assert "AOP 3" in aops
    assert "AOP 1" in aops

    # AOP 1 had no status binding — must map to "Unknown"
    assert aops["AOP 1"]["status"] == "Unknown"
    # AOP 3 had a real status
    assert aops["AOP 3"]["status"] == "WPHA/WNT Endorsed"


# ---------------------------------------------------------------------------
# Test 2: Verbatim preservation of out-of-vocabulary status strings
# ---------------------------------------------------------------------------

def test_unknown_status_value_preserved_verbatim(monkeypatch):
    """
    A status value not in the canonical 7-list must be preserved verbatim,
    NOT dropped or raised (Pitfall 4: never normalize or reject statuses).
    """
    monkeypatch.setattr(oecd, "fetch_aop_oecd_statuses", _mock_fetch)

    result = oecd.build_oecd_status_index()
    aops = result["aops"]

    assert "AOP 999" in aops
    assert aops["AOP 999"]["status"] == "Experimental Stage"


# ---------------------------------------------------------------------------
# Test 3: Every entry has a non-empty status string and a title
# ---------------------------------------------------------------------------

def test_every_aop_entry_has_status_and_title(monkeypatch):
    """
    build_oecd_status_index() must produce an aops dict where every entry
    has a non-empty status string and a non-empty title.
    """
    monkeypatch.setattr(oecd, "fetch_aop_oecd_statuses", _mock_fetch)

    result = oecd.build_oecd_status_index()

    for label, entry in result["aops"].items():
        assert entry.get("status"), f"{label} has empty/missing status"
        assert entry.get("title"), f"{label} has empty/missing title"


# ---------------------------------------------------------------------------
# Test 4: _meta structure — generated_at, source, 8-item vocabulary
# ---------------------------------------------------------------------------

def test_meta_block_structure(monkeypatch):
    """
    The output dict must have a _meta key containing:
      - generated_at (non-empty string)
      - source (the SPARQL endpoint URL)
      - vocabulary with exactly 8 items (7 canonical + "Unknown")
    """
    monkeypatch.setattr(oecd, "fetch_aop_oecd_statuses", _mock_fetch)

    result = oecd.build_oecd_status_index()
    meta = result["_meta"]

    assert meta.get("generated_at"), "_meta.generated_at is missing or empty"
    assert meta.get("source") == oecd.AOPWIKI_SPARQL_ENDPOINT
    assert "vocabulary" in meta
    assert len(meta["vocabulary"]) == 8, (
        f"Expected 8-item vocabulary (7 canonical + 'Unknown'), got {len(meta['vocabulary'])}: {meta['vocabulary']}"
    )
    assert "Unknown" in meta["vocabulary"]
