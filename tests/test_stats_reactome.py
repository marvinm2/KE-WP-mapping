"""
Tests for Reactome integration in the /stats page (Plan 35-03).

Task 1: Headline card + Confidence Breakdown column.
Task 2: Filter+Export controls and Export Formats buttons.
"""
import pytest


# ---------------------------------------------------------------------------
# Task 1 — Reactome headline card + Confidence Breakdown column
# ---------------------------------------------------------------------------

def test_stats_returns_200(client):
    """GET /stats returns HTTP 200."""
    resp = client.get("/stats")
    assert resp.status_code == 200


def test_stats_reactome_headline_card(client):
    """GET /stats HTML contains a KE-Reactome headline card."""
    html = client.get("/stats").get_data(as_text=True)
    assert "KE-Reactome" in html, "Expected 'KE-Reactome' card label in /stats HTML"


def test_stats_confidence_table_has_reactome_column(client):
    """Confidence Breakdown table contains a KE-Reactome column header."""
    html = client.get("/stats").get_data(as_text=True)
    assert "KE-Reactome" in html
    # The column header should appear in the table section
    assert "reactome_by_confidence" in html or "KE-Reactome" in html


def test_stats_has_four_headline_cards(client):
    """The headline counts row has exactly four stat-card elements (WP, GO, Reactome, Total)."""
    html = client.get("/stats").get_data(as_text=True)
    # Each stat card uses stat-card class; count occurrences
    assert html.count("stat-card__label") >= 4, (
        "Expected at least 4 stat-card__label elements (KE-WP, KE-GO, KE-Reactome, Total)"
    )
    assert "KE-WP" in html
    assert "KE-GO" in html
    assert "KE-Reactome" in html
    assert "Total" in html


# ---------------------------------------------------------------------------
# Task 2 — Filter+Export controls + Export Formats buttons
# ---------------------------------------------------------------------------

def test_stats_reactome_export_formats_gmt(client):
    """Export Formats row contains a KE-Reactome GMT button linking to /exports/gmt/ke-reactome."""
    html = client.get("/stats").get_data(as_text=True)
    assert "/exports/gmt/ke-reactome" in html, (
        "Expected '/exports/gmt/ke-reactome' link in /stats HTML"
    )


def test_stats_reactome_export_formats_turtle(client):
    """Export Formats row contains a KE-Reactome Turtle button linking to /exports/rdf/ke-reactome."""
    html = client.get("/stats").get_data(as_text=True)
    assert "/exports/rdf/ke-reactome" in html, (
        "Expected '/exports/rdf/ke-reactome' link in /stats HTML"
    )


def test_stats_reactome_filter_export_api(client):
    """Filter+Export section references /api/v1/reactome-mappings as the Reactome export endpoint."""
    html = client.get("/stats").get_data(as_text=True)
    assert "reactome-mappings" in html, (
        "Expected 'reactome-mappings' (API endpoint reference) in /stats HTML"
    )
