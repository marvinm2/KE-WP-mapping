"""Phase 35 (AUTH-04) — DB-level provider-prefixed identity enforcement.

Regression suite for _migrate_identity_check_constraint: BEFORE INSERT/UPDATE
triggers that abort any write where an identity-bearing column is non-NULL
and does not contain a ':' separator.

Test layout (mirrors Phase 34 migration tests in structure):
  1. Un-prefixed provider_username in proposals is rejected (IntegrityError).
  2. Properly-prefixed provider_username in proposals succeeds.
  3. Un-prefixed created_by in mappings is rejected; prefixed value succeeds.
  4. _ensure_schema is idempotent — running Database() twice raises no error.
"""
import sqlite3
import uuid

import pytest

from src.core.models import Database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _insert_proposal(conn, provider_username):
    """Minimal proposals INSERT — only provider_username is constrained here."""
    conn.execute(
        "INSERT INTO proposals (ke_id, ke_title, wp_id, wp_title, provider_username) "
        "VALUES (?, ?, ?, ?, ?)",
        ("KE:1", "Test KE", "WP1", "Test Pathway", provider_username),
    )
    conn.commit()


def _insert_mapping(conn, created_by):
    """Minimal mappings INSERT with a given created_by value."""
    conn.execute(
        "INSERT INTO mappings (uuid, ke_id, ke_title, wp_id, wp_title, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), "KE:2", "Test KE 2", "WP2", "Test Pathway 2", created_by),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Test 1: un-prefixed provider_username is rejected
# ---------------------------------------------------------------------------

def test_proposals_unprefixed_provider_username_rejected(tmp_path):
    """INSERT into proposals with provider_username lacking ':' must raise IntegrityError."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)
    conn = _open(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            _insert_proposal(conn, "alice")  # no provider: prefix — must be rejected
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Test 2: prefixed provider_username succeeds
# ---------------------------------------------------------------------------

def test_proposals_prefixed_provider_username_succeeds(tmp_path):
    """INSERT into proposals with provider_username='github:alice' must succeed."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)
    conn = _open(db_path)
    try:
        _insert_proposal(conn, "github:alice")  # valid prefix — must succeed
        row = conn.execute(
            "SELECT provider_username FROM proposals WHERE ke_id='KE:1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "github:alice"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Test 3: mappings created_by enforcement
# ---------------------------------------------------------------------------

def test_mappings_unprefixed_created_by_rejected(tmp_path):
    """INSERT into mappings with created_by lacking ':' must raise IntegrityError."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)
    conn = _open(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            _insert_mapping(conn, "plain-username")  # must be rejected
    finally:
        conn.close()


def test_mappings_prefixed_created_by_succeeds(tmp_path):
    """INSERT into mappings with created_by='orcid:0000-0003-2230-0840' must succeed."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)
    conn = _open(db_path)
    try:
        _insert_mapping(conn, "orcid:0000-0003-2230-0840")
        row = conn.execute(
            "SELECT created_by FROM mappings WHERE ke_id='KE:2'"
        ).fetchone()
        assert row is not None
        assert row[0] == "orcid:0000-0003-2230-0840"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Test 4: idempotency — running Database() twice raises no error
# ---------------------------------------------------------------------------

def test_schema_init_is_idempotent(tmp_path):
    """Calling Database() twice on the same file must not raise (CREATE TRIGGER IF NOT EXISTS)."""
    db_path = str(tmp_path / "test.db")
    Database(db_path)   # First init: triggers created
    Database(db_path)   # Second init: IF NOT EXISTS guards, no-ops
    # If we got here without raising, idempotency holds.
