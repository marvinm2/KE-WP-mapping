"""
Database models for KE-WP Mapping Application
"""
import logging
import secrets
import sqlite3
import uuid as uuid_lib
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "ke_wp_mapping.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get database connection with WAL mode, busy timeout, and row factory."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def init_db(self):
        """Initialize database with required tables"""
        conn = self.get_connection()
        try:
            # Create mappings table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ke_id TEXT NOT NULL,
                    ke_title TEXT NOT NULL,
                    wp_id TEXT NOT NULL,
                    wp_title TEXT NOT NULL,
                    connection_type TEXT NOT NULL DEFAULT 'undefined',
                    confidence_level TEXT NOT NULL DEFAULT 'low',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ke_id, wp_id)
                )
            """
            )

            # Create proposals table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mapping_id INTEGER,
                    user_name TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    user_affiliation TEXT NOT NULL,
                    github_username TEXT,
                    proposed_delete BOOLEAN DEFAULT FALSE,
                    proposed_confidence TEXT,
                    proposed_connection_type TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mapping_id) REFERENCES mappings (id)
                )
            """
            )

            # Create cache table for SPARQL responses
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sparql_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    response_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    UNIQUE(endpoint, query_hash)
                )
            """
            )

            # Create indexes for performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mappings_ke_id ON mappings(ke_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mappings_wp_id ON mappings(wp_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mappings_created_by ON mappings(created_by)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_proposals_mapping_id ON proposals(mapping_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_expires ON sparql_cache(expires_at)"
            )

            # Create KE-GO mappings table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ke_go_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ke_id TEXT NOT NULL,
                    ke_title TEXT NOT NULL,
                    go_id TEXT NOT NULL,
                    go_name TEXT NOT NULL,
                    connection_type TEXT NOT NULL DEFAULT 'related',
                    confidence_level TEXT NOT NULL DEFAULT 'low',
                    evidence_code TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ke_id, go_id)
                )
            """
            )

            # Create KE-GO proposals table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ke_go_proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mapping_id INTEGER,
                    user_name TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    user_affiliation TEXT NOT NULL,
                    github_username TEXT,
                    proposed_delete BOOLEAN DEFAULT FALSE,
                    proposed_confidence TEXT,
                    proposed_connection_type TEXT,
                    status TEXT DEFAULT 'pending',
                    admin_notes TEXT,
                    approved_by TEXT,
                    approved_at TIMESTAMP,
                    rejected_by TEXT,
                    rejected_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mapping_id) REFERENCES ke_go_mappings(id)
                )
            """
            )

            # Create indexes for GO mappings
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_go_mappings_ke_id ON ke_go_mappings(ke_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_go_mappings_go_id ON ke_go_mappings(go_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_go_proposals_mapping_id ON ke_go_proposals(mapping_id)"
            )

            # Create guest codes table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS guest_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    max_uses INTEGER DEFAULT 1,
                    use_count INTEGER DEFAULT 0,
                    is_revoked BOOLEAN DEFAULT FALSE,
                    revoked_at TIMESTAMP,
                    revoked_by TEXT
                )
            """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_guest_codes_code ON guest_codes(code)"
            )

            # Migrate proposals table to add admin fields if needed
            self._migrate_proposals_admin_fields(conn)

            # Migrate mappings table to add updated_by field if needed
            self._migrate_mappings_updated_by_field(conn)

            # Migrate mapping tables to add uuid and provenance columns (Phase 2)
            self._migrate_mappings_uuid_and_provenance(conn)
            self._migrate_go_mappings_uuid_and_provenance(conn)

            # Migrate proposal tables to add phase 2 fields (Phase 2)
            self._migrate_proposals_phase2_fields(conn)
            self._migrate_go_proposals_phase2_fields(conn)

            # Migrate mappings/go_mappings tables to add Phase 3 columns
            self._migrate_mappings_suggestion_score(conn)
            self._migrate_go_mappings_suggestion_score(conn)
            self._migrate_go_mappings_go_namespace(conn)

            # Migrate proposals table to add new-pair fields (Phase 3 gap closure)
            self._migrate_proposals_new_pair_fields(conn)

            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Database initialization failed: %s", e)
            conn.rollback()
            raise
        finally:
            conn.close()

    def _migrate_proposals_admin_fields(self, conn):
        """
        Add admin fields to proposals table if they don't exist

        Args:
            conn: Database connection
        """
        try:
            # Check if admin fields exist
            cursor = conn.execute("PRAGMA table_info(proposals)")
            columns = [row[1] for row in cursor.fetchall()]

            admin_fields = [
                "admin_notes",
                "approved_by",
                "approved_at",
                "rejected_by",
                "rejected_at",
            ]
            missing_fields = [field for field in admin_fields if field not in columns]

            if missing_fields:
                logger.info(
                    "Adding missing admin fields to proposals table: %s", missing_fields
                )

                for field in missing_fields:
                    if field.endswith("_at"):
                        conn.execute(
                            f"ALTER TABLE proposals ADD COLUMN {field} TIMESTAMP"
                        )
                    else:
                        conn.execute(f"ALTER TABLE proposals ADD COLUMN {field} TEXT")

                logger.info("Successfully migrated proposals table with admin fields")

        except Exception as e:
            logger.error("Error migrating proposals table: %s", e)
            raise

    def _migrate_mappings_updated_by_field(self, conn):
        """
        Add updated_by field to mappings table if it doesn't exist

        Args:
            conn: Database connection
        """
        try:
            # Check if updated_by field exists
            cursor = conn.execute("PRAGMA table_info(mappings)")
            columns = [row[1] for row in cursor.fetchall()]

            if "updated_by" not in columns:
                logger.info("Adding missing updated_by field to mappings table")
                conn.execute("ALTER TABLE mappings ADD COLUMN updated_by TEXT")
                logger.info("Successfully migrated mappings table with updated_by field")

        except Exception as e:
            logger.error("Error migrating mappings table: %s", e)
            raise

    def _migrate_mappings_uuid_and_provenance(self, conn):
        """
        Add uuid and curator provenance columns to mappings table if they don't exist.

        Columns added:
            - uuid TEXT  — stable UUID per row (backfilled for existing rows)
            - approved_by_curator TEXT — GitHub username of curator who approved
            - approved_at_curator TIMESTAMP — when curator approved

        Args:
            conn: Database connection
        """
        try:
            cursor = conn.execute("PRAGMA table_info(mappings)")
            columns = [row[1] for row in cursor.fetchall()]

            new_columns = []
            if "uuid" not in columns:
                conn.execute("ALTER TABLE mappings ADD COLUMN uuid TEXT")
                new_columns.append("uuid")
            if "approved_by_curator" not in columns:
                conn.execute("ALTER TABLE mappings ADD COLUMN approved_by_curator TEXT")
                new_columns.append("approved_by_curator")
            if "approved_at_curator" not in columns:
                conn.execute(
                    "ALTER TABLE mappings ADD COLUMN approved_at_curator TIMESTAMP"
                )
                new_columns.append("approved_at_curator")

            # Backfill uuid for any rows where uuid IS NULL
            conn.execute(
                """
                UPDATE mappings SET uuid = lower(hex(randomblob(4))) || '-' ||
                lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) ||
                '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                substr(lower(hex(randomblob(2))),2) || '-' ||
                lower(hex(randomblob(6)))
                WHERE uuid IS NULL
                """
            )

            # Ensure unique index on uuid
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_mappings_uuid ON mappings(uuid)"
            )

            if new_columns:
                logger.info(
                    "Migrated mappings table with uuid and provenance columns: %s",
                    new_columns,
                )

        except Exception as e:
            logger.error("Error migrating mappings uuid/provenance columns: %s", e)
            raise

    def _migrate_go_mappings_uuid_and_provenance(self, conn):
        """
        Add uuid and curator provenance columns to ke_go_mappings table if they don't exist.

        Columns added:
            - uuid TEXT  — stable UUID per row (backfilled for existing rows)
            - approved_by_curator TEXT — GitHub username of curator who approved
            - approved_at_curator TIMESTAMP — when curator approved

        Args:
            conn: Database connection
        """
        try:
            cursor = conn.execute("PRAGMA table_info(ke_go_mappings)")
            columns = [row[1] for row in cursor.fetchall()]

            new_columns = []
            if "uuid" not in columns:
                conn.execute("ALTER TABLE ke_go_mappings ADD COLUMN uuid TEXT")
                new_columns.append("uuid")
            if "approved_by_curator" not in columns:
                conn.execute(
                    "ALTER TABLE ke_go_mappings ADD COLUMN approved_by_curator TEXT"
                )
                new_columns.append("approved_by_curator")
            if "approved_at_curator" not in columns:
                conn.execute(
                    "ALTER TABLE ke_go_mappings ADD COLUMN approved_at_curator TIMESTAMP"
                )
                new_columns.append("approved_at_curator")

            # Backfill uuid for any rows where uuid IS NULL
            conn.execute(
                """
                UPDATE ke_go_mappings SET uuid = lower(hex(randomblob(4))) || '-' ||
                lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) ||
                '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                substr(lower(hex(randomblob(2))),2) || '-' ||
                lower(hex(randomblob(6)))
                WHERE uuid IS NULL
                """
            )

            # Ensure unique index on uuid
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_go_mappings_uuid ON ke_go_mappings(uuid)"
            )

            if new_columns:
                logger.info(
                    "Migrated ke_go_mappings table with uuid and provenance columns: %s",
                    new_columns,
                )

        except Exception as e:
            logger.error("Error migrating ke_go_mappings uuid/provenance columns: %s", e)
            raise

    def _migrate_proposals_phase2_fields(self, conn):
        """
        Add Phase 2 fields to proposals table if they don't exist.

        Columns added:
            - uuid TEXT — stable UUID assigned at proposal creation time
            - suggestion_score REAL — BioBERT hybrid score from suggestion card
            - is_stale BOOLEAN DEFAULT FALSE — curator flag for admin review

        Args:
            conn: Database connection
        """
        try:
            cursor = conn.execute("PRAGMA table_info(proposals)")
            columns = [row[1] for row in cursor.fetchall()]

            new_columns = []
            if "uuid" not in columns:
                conn.execute("ALTER TABLE proposals ADD COLUMN uuid TEXT")
                new_columns.append("uuid")
            if "suggestion_score" not in columns:
                conn.execute("ALTER TABLE proposals ADD COLUMN suggestion_score REAL")
                new_columns.append("suggestion_score")
            if "is_stale" not in columns:
                conn.execute(
                    "ALTER TABLE proposals ADD COLUMN is_stale BOOLEAN DEFAULT FALSE"
                )
                new_columns.append("is_stale")

            if new_columns:
                logger.info(
                    "Migrated proposals table with Phase 2 fields: %s", new_columns
                )

        except Exception as e:
            logger.error("Error migrating proposals Phase 2 fields: %s", e)
            raise

    def _migrate_go_proposals_phase2_fields(self, conn):
        """
        Add Phase 2 fields to ke_go_proposals table if they don't exist.

        Columns added:
            - uuid TEXT — stable UUID assigned at proposal creation time
            - suggestion_score REAL — BioBERT hybrid score from suggestion card
            - is_stale BOOLEAN DEFAULT FALSE — curator flag for admin review

        Note: ke_go_proposals already has approved_by, approved_at, rejected_by,
        rejected_at from its CREATE TABLE definition — these are not re-added.

        Args:
            conn: Database connection
        """
        try:
            cursor = conn.execute("PRAGMA table_info(ke_go_proposals)")
            columns = [row[1] for row in cursor.fetchall()]

            new_columns = []
            if "uuid" not in columns:
                conn.execute("ALTER TABLE ke_go_proposals ADD COLUMN uuid TEXT")
                new_columns.append("uuid")
            if "suggestion_score" not in columns:
                conn.execute(
                    "ALTER TABLE ke_go_proposals ADD COLUMN suggestion_score REAL"
                )
                new_columns.append("suggestion_score")
            if "is_stale" not in columns:
                conn.execute(
                    "ALTER TABLE ke_go_proposals ADD COLUMN is_stale BOOLEAN DEFAULT FALSE"
                )
                new_columns.append("is_stale")

            if new_columns:
                logger.info(
                    "Migrated ke_go_proposals table with Phase 2 fields: %s", new_columns
                )

        except Exception as e:
            logger.error("Error migrating ke_go_proposals Phase 2 fields: %s", e)
            raise

    def _migrate_mappings_suggestion_score(self, conn):
        """
        Add suggestion_score column to mappings table if it does not exist.

        suggestion_score (REAL, nullable) — BioBERT hybrid score copied from
        the approved proposal at admin approval time. NULL for all pre-Phase-3
        rows (score was only stored on proposals before this migration).
        """
        try:
            cursor = conn.execute("PRAGMA table_info(mappings)")
            columns = [row[1] for row in cursor.fetchall()]
            if "suggestion_score" not in columns:
                conn.execute("ALTER TABLE mappings ADD COLUMN suggestion_score REAL")
                logger.info("Migrated mappings table: added suggestion_score column")
        except Exception as e:
            logger.error("Error migrating mappings suggestion_score: %s", e)
            raise

    def _migrate_go_mappings_suggestion_score(self, conn):
        """
        Add suggestion_score column to ke_go_mappings table if it does not exist.

        suggestion_score (REAL, nullable) — BioBERT hybrid score copied from
        the approved GO proposal at admin approval time. NULL for all pre-Phase-3
        rows (score was only stored on proposals before this migration).
        """
        try:
            cursor = conn.execute("PRAGMA table_info(ke_go_mappings)")
            columns = [row[1] for row in cursor.fetchall()]
            if "suggestion_score" not in columns:
                conn.execute(
                    "ALTER TABLE ke_go_mappings ADD COLUMN suggestion_score REAL"
                )
                logger.info(
                    "Migrated ke_go_mappings table: added suggestion_score column"
                )
        except Exception as e:
            logger.error("Error migrating ke_go_mappings suggestion_score: %s", e)
            raise

    def _migrate_go_mappings_go_namespace(self, conn):
        """
        Add go_namespace column to ke_go_mappings table if it does not exist.

        go_namespace (TEXT, NOT NULL, DEFAULT 'biological_process') — the ontology
        namespace for the GO term. All current GO mappings are Biological Process;
        the column is present for extensibility when MF/CC mappings are added.
        Existing rows receive 'biological_process' via the DEFAULT.
        """
        try:
            cursor = conn.execute("PRAGMA table_info(ke_go_mappings)")
            columns = [row[1] for row in cursor.fetchall()]
            if "go_namespace" not in columns:
                conn.execute(
                    "ALTER TABLE ke_go_mappings ADD COLUMN "
                    "go_namespace TEXT NOT NULL DEFAULT 'biological_process'"
                )
                logger.info(
                    "Migrated ke_go_mappings table: added go_namespace column"
                )
        except Exception as e:
            logger.error("Error migrating ke_go_mappings go_namespace: %s", e)
            raise

    def _migrate_proposals_new_pair_fields(self, conn):
        """
        Add new-pair columns to proposals table if they don't exist.

        New-pair proposals (mapping_id=NULL) need to store the pair data that would
        normally come from the joined mappings row.

        Columns added:
            - ke_id TEXT — Key Event ID for new-pair proposals
            - ke_title TEXT — Key Event title for new-pair proposals
            - wp_id TEXT — WikiPathways ID for new-pair proposals
            - wp_title TEXT — WikiPathways title for new-pair proposals
            - new_pair_connection_type TEXT — connection type for new-pair proposals
            - new_pair_confidence_level TEXT — confidence level for new-pair proposals

        Args:
            conn: Database connection
        """
        try:
            cursor = conn.execute("PRAGMA table_info(proposals)")
            columns = [row[1] for row in cursor.fetchall()]

            new_columns = []
            fields_to_add = [
                ("ke_id", "TEXT"),
                ("ke_title", "TEXT"),
                ("wp_id", "TEXT"),
                ("wp_title", "TEXT"),
                ("new_pair_connection_type", "TEXT"),
                ("new_pair_confidence_level", "TEXT"),
            ]
            for field_name, field_type in fields_to_add:
                if field_name not in columns:
                    conn.execute(
                        f"ALTER TABLE proposals ADD COLUMN {field_name} {field_type}"
                    )
                    new_columns.append(field_name)

            if new_columns:
                logger.info(
                    "Migrated proposals table with new-pair fields: %s", new_columns
                )

        except Exception as e:
            logger.error("Error migrating proposals new-pair fields: %s", e)
            raise


class MappingModel:
    def __init__(self, db: Database):
        self.db = db

    def create_mapping(
        self,
        ke_id: str,
        ke_title: str,
        wp_id: str,
        wp_title: str,
        connection_type: str = "undefined",
        confidence_level: str = "low",
        created_by: str = None,
    ) -> Optional[int]:
        """Create a new KE-WP mapping"""
        mapping_uuid = str(uuid_lib.uuid4())
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title, connection_type,
                                    confidence_level, created_by, uuid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    ke_id,
                    ke_title,
                    wp_id,
                    wp_title,
                    connection_type,
                    confidence_level,
                    created_by,
                    mapping_uuid,
                ),
            )

            conn.commit()
            logger.info(
                "Created mapping: KE=%s, WP=%s, User=%s, UUID=%s",
                ke_id,
                wp_id,
                created_by,
                mapping_uuid,
            )
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning("Duplicate mapping attempted: KE=%s, WP=%s", ke_id, wp_id)
            return None
        except Exception as e:
            logger.error("Error creating mapping: %s", e)
            conn.rollback()
            return None
        finally:
            conn.close()

    def get_all_mappings(self) -> List[Dict]:
        """Get all mappings"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, ke_id, ke_title, wp_id, wp_title, connection_type,
                       confidence_level, created_by, created_at, updated_at,
                       uuid, approved_by_curator, approved_at_curator
                FROM mappings
                ORDER BY created_at DESC
            """
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_mappings_by_ke(self, ke_id: str) -> List[Dict]:
        """Get all mappings for a specific Key Event"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, ke_id, ke_title, wp_id, wp_title, connection_type,
                       confidence_level, created_by, created_at, updated_at,
                       uuid, approved_by_curator, approved_at_curator
                FROM mappings
                WHERE ke_id = ?
                ORDER BY created_at DESC
                """,
                (ke_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_mappings_paginated(
        self,
        page: int = 1,
        per_page: int = 50,
        ke_id: str = None,
        pathway_id: str = None,
        confidence_level: str = None,
        ke_ids: list = None,
    ) -> tuple:
        """
        Return (List[Dict], total_count) for approved KE-WP mappings.

        Filters (all optional, combinable):
          ke_id            — exact match on mappings.ke_id
          pathway_id       — exact match on mappings.wp_id
          confidence_level — case-insensitive match on mappings.confidence_level
          ke_ids           — IN filter used when aop_id has been resolved to KE IDs;
                             pass [] to return ([], 0) immediately (valid AOP, no KEs mapped)

        Returns rows with columns:
          uuid, ke_id, ke_title, wp_id, wp_title, confidence_level,
          approved_by_curator, approved_at_curator, suggestion_score
        Ordered by created_at DESC.
        """
        conditions = []
        params = []

        if ke_id:
            conditions.append("ke_id = ?")
            params.append(ke_id)
        if pathway_id:
            conditions.append("wp_id = ?")
            params.append(pathway_id)
        if confidence_level:
            conditions.append("LOWER(confidence_level) = LOWER(?)")
            params.append(confidence_level)
        if ke_ids is not None:
            if not ke_ids:
                return [], 0
            placeholders = ",".join("?" * len(ke_ids))
            conditions.append(f"ke_id IN ({placeholders})")
            params.extend(ke_ids)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * per_page

        conn = self.db.get_connection()
        try:
            total = conn.execute(
                f"SELECT COUNT(*) FROM mappings {where}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"""SELECT uuid, ke_id, ke_title, wp_id, wp_title, confidence_level,
                           approved_by_curator, approved_at_curator, suggestion_score
                    FROM mappings {where}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?""",
                params + [per_page, offset],
            ).fetchall()
            return [dict(r) for r in rows], total
        finally:
            conn.close()

    def check_mapping_exists(self, ke_id: str, wp_id: str) -> Dict:
        """Check if KE-WP pair exists"""
        conn = self.db.get_connection()
        try:
            # Check exact pair
            cursor = conn.execute(
                """
                SELECT * FROM mappings WHERE ke_id = ? AND wp_id = ?
            """,
                (ke_id, wp_id),
            )
            pair_match = cursor.fetchone()

            if pair_match:
                return {
                    "pair_exists": True,
                    "message": f"The KE-WP pair ({ke_id}, {wp_id}) already exists.",
                }

            # Check for existing KE
            cursor = conn.execute(
                """
                SELECT * FROM mappings WHERE ke_id = ?
            """,
                (ke_id,),
            )
            ke_matches = [dict(row) for row in cursor.fetchall()]

            if ke_matches:
                return {
                    "ke_exists": True,
                    "message": f"The KE ID {ke_id} exists but not with WP ID {wp_id}.",
                    "ke_matches": ke_matches,
                }

            return {
                "ke_exists": False,
                "pair_exists": False,
                "message": f"The KE ID {ke_id} and WP ID {wp_id} are new entries.",
            }
        finally:
            conn.close()

    def check_mapping_exists_with_proposals(self, ke_id: str, wp_id: str) -> Dict:
        """
        Enriched duplicate check that returns structured blocking payloads.

        Priority order:
        1. pending_proposal — an open proposal already covers this pair (most actionable)
        2. approved_mapping — approved mapping exists, user can submit_revision
        3. ke_exists — KE exists with a different WP (informational)
        4. nothing found

        Returns one of:
        - blocking_type='pending_proposal' if a pending proposal exists for the pair
        - blocking_type='approved_mapping' if an approved KE-WP pair exists (no pending proposal)
        - ke_exists info if the KE exists with a different WP
        - ke_exists=False, pair_exists=False if nothing found
        """
        conn = self.db.get_connection()
        try:
            # 1. Check for pending proposal on the KE-WP pair (highest priority blocking)
            cursor = conn.execute(
                """
                SELECT p.id, p.proposed_confidence, p.proposed_connection_type,
                       p.github_username, p.created_at,
                       m.ke_id, m.wp_id, m.ke_title, m.wp_title
                FROM proposals p
                JOIN mappings m ON p.mapping_id = m.id
                WHERE m.ke_id = ? AND m.wp_id = ? AND p.status = 'pending'
                ORDER BY p.created_at DESC LIMIT 1
                """,
                (ke_id, wp_id),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "pair_exists": True,
                    "blocking_type": "pending_proposal",
                    "existing": {
                        "proposal_id": row["id"],
                        "ke_id": row["ke_id"],
                        "wp_id": row["wp_id"],
                        "ke_title": row["ke_title"],
                        "wp_title": row["wp_title"],
                        "proposed_confidence": row["proposed_confidence"],
                        "proposed_connection_type": row["proposed_connection_type"],
                        "submitted_by": row["github_username"],
                        "submitted_at": row["created_at"],
                    },
                    "actions": ["flag_stale"],
                }

            # 2. Check for approved mapping (exact ke_id + wp_id pair)
            cursor = conn.execute(
                """
                SELECT id, ke_id, ke_title, wp_id, wp_title, connection_type,
                       confidence_level, approved_by_curator, approved_at_curator, uuid
                FROM mappings WHERE ke_id = ? AND wp_id = ?
                """,
                (ke_id, wp_id),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "pair_exists": True,
                    "blocking_type": "approved_mapping",
                    "existing": {
                        "ke_id": row["ke_id"],
                        "wp_id": row["wp_id"],
                        "ke_title": row["ke_title"],
                        "wp_title": row["wp_title"],
                        "confidence_level": row["confidence_level"],
                        "connection_type": row["connection_type"],
                        "approved_by_curator": row["approved_by_curator"],
                        "approved_at_curator": row["approved_at_curator"],
                        "uuid": row["uuid"],
                        "id": row["id"],
                    },
                    "actions": ["submit_revision"],
                }

            # 3. Check if KE exists with a different WP (backward-compat ke_exists path)
            cursor = conn.execute(
                "SELECT * FROM mappings WHERE ke_id = ?",
                (ke_id,),
            )
            ke_matches = [dict(row) for row in cursor.fetchall()]
            if ke_matches:
                return {
                    "ke_exists": True,
                    "message": f"The KE ID {ke_id} exists but not with WP ID {wp_id}.",
                    "ke_matches": ke_matches,
                }

            return {
                "ke_exists": False,
                "pair_exists": False,
                "message": f"The KE ID {ke_id} and WP ID {wp_id} are new entries.",
            }
        finally:
            conn.close()

    def update_mapping(
        self,
        mapping_id: int,
        connection_type: str = None,
        confidence_level: str = None,
        updated_by: str = None,
        approved_by_curator: str = None,
        approved_at_curator: str = None,
        suggestion_score: float = None,
    ) -> bool:
        """
        Update an existing mapping

        Args:
            mapping_id: ID of the mapping to update
            connection_type: New connection type (optional)
            confidence_level: New confidence level (optional)
            updated_by: Username of person making the update
            approved_by_curator: GitHub username of curator who approved (optional)
            approved_at_curator: ISO timestamp of curator approval (optional)
            suggestion_score: BioBERT hybrid score from the approved proposal (optional)

        Returns:
            True if successful, False otherwise
        """
        # Define allowed fields to prevent SQL injection
        ALLOWED_FIELDS = {
            "connection_type": "connection_type",
            "confidence_level": "confidence_level",
            "updated_by": "updated_by",
            "approved_by_curator": "approved_by_curator",
            "approved_at_curator": "approved_at_curator",
            "suggestion_score": "suggestion_score",
        }

        conn = self.db.get_connection()
        try:
            update_clauses = []
            params = []

            # Build update clauses using whitelisted field names
            update_data = {
                "connection_type": connection_type,
                "confidence_level": confidence_level,
                "updated_by": updated_by,
                "approved_by_curator": approved_by_curator,
                "approved_at_curator": approved_at_curator,
                "suggestion_score": suggestion_score,
            }

            for field_name, field_value in update_data.items():
                if field_value is not None and field_name in ALLOWED_FIELDS:
                    update_clauses.append(f"{ALLOWED_FIELDS[field_name]} = ?")
                    params.append(field_value)

            # Always update timestamp
            update_clauses.append("updated_at = CURRENT_TIMESTAMP")

            if not update_clauses:
                return False

            # Build safe query with whitelisted field names
            query = f"UPDATE mappings SET {', '.join(update_clauses)} WHERE id = ?"
            params.append(mapping_id)

            conn.execute(query, params)
            conn.commit()
            logger.info("Updated mapping %s by %s", mapping_id, updated_by)
            return True
        except Exception as e:
            logger.error("Error updating mapping: %s", e)
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_mapping_by_uuid(self, mapping_uuid: str) -> Optional[Dict]:
        """Get a mapping by its stable UUID"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, ke_id, ke_title, wp_id, wp_title, connection_type,
                       confidence_level, created_by, created_at, updated_at,
                       uuid, approved_by_curator, approved_at_curator, updated_by
                FROM mappings
                WHERE uuid = ?
                """,
                (mapping_uuid,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_mapping(self, mapping_id: int, deleted_by: str = None) -> bool:
        """
        Delete a mapping

        Args:
            mapping_id: ID of the mapping to delete
            deleted_by: Username of person deleting the mapping

        Returns:
            True if successful, False otherwise
        """
        conn = self.db.get_connection()
        try:
            conn.execute("DELETE FROM mappings WHERE id = ?", (mapping_id,))
            conn.commit()
            logger.info("Deleted mapping %s by %s", mapping_id, deleted_by)
            return True
        except Exception as e:
            logger.error("Error deleting mapping: %s", e)
            conn.rollback()
            return False
        finally:
            conn.close()


class ProposalModel:
    def __init__(self, db: Database):
        self.db = db

    def create_proposal(
        self,
        mapping_id: int,
        user_name: str,
        user_email: str,
        user_affiliation: str,
        github_username: str = None,
        proposed_delete: bool = False,
        proposed_confidence: str = None,
        proposed_connection_type: str = None,
    ) -> Optional[int]:
        """Create a new proposal"""
        proposal_uuid = str(uuid_lib.uuid4())
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO proposals (mapping_id, user_name, user_email, user_affiliation,
                                     github_username, proposed_delete, proposed_confidence,
                                     proposed_connection_type, uuid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    mapping_id,
                    user_name,
                    user_email,
                    user_affiliation,
                    github_username,
                    proposed_delete,
                    proposed_confidence,
                    proposed_connection_type,
                    proposal_uuid,
                ),
            )

            conn.commit()
            logger.info(
                "Created proposal for mapping %s by %s, UUID=%s",
                mapping_id,
                github_username,
                proposal_uuid,
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error("Error creating proposal: %s", e)
            conn.rollback()
            return None
        finally:
            conn.close()

    def create_new_pair_proposal(
        self,
        ke_id: str,
        ke_title: str,
        wp_id: str,
        wp_title: str,
        connection_type: str,
        confidence_level: str,
        github_username: str = None,
        suggestion_score: float = None,
    ) -> Optional[int]:
        """
        Create a new-pair proposal where no existing mapping_id exists yet.

        The mapping is created only after an admin explicitly approves this proposal.
        mapping_id is left NULL so approve_proposal() knows to call create_mapping()
        rather than update_mapping() at approval time.

        Args:
            ke_id: Key Event ID
            ke_title: Key Event title
            wp_id: WikiPathways ID
            wp_title: WikiPathways title
            connection_type: Proposed connection type
            confidence_level: Proposed confidence level
            github_username: GitHub username of submitting curator
            suggestion_score: BioBERT hybrid score captured at suggestion time

        Returns:
            New proposal row ID on success, None on exception
        """
        proposal_uuid = str(uuid_lib.uuid4())
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO proposals (
                    mapping_id, user_name, user_email, user_affiliation,
                    github_username, proposed_delete, proposed_confidence,
                    proposed_connection_type, uuid, suggestion_score,
                    ke_id, ke_title, wp_id, wp_title,
                    new_pair_connection_type, new_pair_confidence_level
                )
                VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    github_username or "curator",
                    "",
                    "",
                    github_username,
                    False,
                    confidence_level,
                    connection_type,
                    proposal_uuid,
                    suggestion_score,
                    ke_id,
                    ke_title,
                    wp_id,
                    wp_title,
                    connection_type,
                    confidence_level,
                ),
            )

            conn.commit()
            logger.info(
                "Created new-pair proposal for %s -> %s by %s, UUID=%s",
                ke_id,
                wp_id,
                github_username,
                proposal_uuid,
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error("Error creating new-pair proposal: %s", e)
            conn.rollback()
            return None
        finally:
            conn.close()

    def get_all_proposals(self, status: str = None) -> List[Dict]:
        """
        Get all proposals, optionally filtered by status

        Args:
            status: Filter by proposal status ('pending', 'approved', 'rejected', or None for all)

        Returns:
            List of proposal dictionaries with mapping details
        """
        conn = self.db.get_connection()
        try:
            query = """
                SELECT p.*, m.ke_id, m.ke_title, m.wp_id, m.wp_title, 
                       m.connection_type as current_connection_type,
                       m.confidence_level as current_confidence_level
                FROM proposals p
                LEFT JOIN mappings m ON p.mapping_id = m.id
            """
            params = ()

            if status:
                query += " WHERE p.status = ?"
                params = (status,)

            query += " ORDER BY p.created_at DESC"

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_proposal_by_id(self, proposal_id: int) -> Optional[Dict]:
        """
        Get a specific proposal by ID with mapping details

        Args:
            proposal_id: The proposal ID to retrieve

        Returns:
            Dictionary containing proposal and mapping details, or None if not found
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT p.*, m.ke_id, m.ke_title, m.wp_id, m.wp_title,
                       m.connection_type as current_connection_type,
                       m.confidence_level as current_confidence_level
                FROM proposals p
                LEFT JOIN mappings m ON p.mapping_id = m.id
                WHERE p.id = ?
            """,
                (proposal_id,),
            )

            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_proposal_status(
        self,
        proposal_id: int,
        status: str,
        admin_username: str = None,
        admin_notes: str = None,
    ) -> bool:
        """
        Update proposal status and admin information

        Args:
            proposal_id: The proposal ID to update
            status: New status ('approved', 'rejected')
            admin_username: GitHub username of admin performing action
            admin_notes: Optional notes from admin

        Returns:
            True if successful, False otherwise
        """
        # Validate status to prevent SQL injection
        if status not in ["approved", "rejected"]:
            logger.error("Invalid status value: %s", status)
            return False

        conn = self.db.get_connection()
        try:
            # Use safe field mapping based on validated status
            if status == "approved":
                query = """
                    UPDATE proposals 
                    SET status = ?, approved_by = ?, admin_notes = ?, approved_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
            else:  # status == 'rejected'
                query = """
                    UPDATE proposals 
                    SET status = ?, rejected_by = ?, admin_notes = ?, rejected_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """

            conn.execute(query, (status, admin_username, admin_notes, proposal_id))

            conn.commit()
            logger.info(
                "Updated proposal %s to %s by %s", proposal_id, status, admin_username
            )
            return True
        except Exception as e:
            logger.error("Error updating proposal status: %s", e)
            conn.rollback()
            return False
        finally:
            conn.close()

    def flag_proposal_stale(self, proposal_id: int, flagged_by: str) -> bool:
        """
        Flag a pending proposal as stale for admin review.

        Args:
            proposal_id: ID of the proposal to flag
            flagged_by: Username of curator flagging the proposal

        Returns:
            True if successful, False otherwise
        """
        conn = self.db.get_connection()
        try:
            conn.execute(
                "UPDATE proposals SET is_stale = 1 WHERE id = ?",
                (proposal_id,),
            )
            conn.commit()
            logger.info(
                "Proposal %s flagged as stale by %s", proposal_id, flagged_by
            )
            return True
        except Exception as e:
            logger.error("Error flagging proposal %s as stale: %s", proposal_id, e)
            conn.rollback()
            return False
        finally:
            conn.close()

    def find_mapping_by_details(self, ke_id: str, wp_id: str) -> Optional[int]:
        """
        Find mapping ID by KE and WP IDs

        Args:
            ke_id: Key Event ID
            wp_id: WikiPathway ID

        Returns:
            Mapping ID if found, None otherwise
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id FROM mappings WHERE ke_id = ? AND wp_id = ?
            """,
                (ke_id, wp_id),
            )

            row = cursor.fetchone()
            return row["id"] if row else None
        finally:
            conn.close()


class GoMappingModel:
    def __init__(self, db: Database):
        self.db = db

    def create_mapping(
        self,
        ke_id: str,
        ke_title: str,
        go_id: str,
        go_name: str,
        connection_type: str = "related",
        confidence_level: str = "low",
        evidence_code: str = None,
        created_by: str = None,
    ) -> Optional[int]:
        """Create a new KE-GO mapping"""
        mapping_uuid = str(uuid_lib.uuid4())
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO ke_go_mappings (ke_id, ke_title, go_id, go_name, connection_type,
                                           confidence_level, evidence_code, created_by, uuid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    ke_id,
                    ke_title,
                    go_id,
                    go_name,
                    connection_type,
                    confidence_level,
                    evidence_code,
                    created_by,
                    mapping_uuid,
                ),
            )

            conn.commit()
            logger.info(
                "Created GO mapping: KE=%s, GO=%s, User=%s, UUID=%s",
                ke_id,
                go_id,
                created_by,
                mapping_uuid,
            )
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning("Duplicate GO mapping attempted: KE=%s, GO=%s", ke_id, go_id)
            return None
        except Exception as e:
            logger.error("Error creating GO mapping: %s", e)
            conn.rollback()
            return None
        finally:
            conn.close()

    def get_all_mappings(self) -> List[Dict]:
        """Get all KE-GO mappings"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, ke_id, ke_title, go_id, go_name, connection_type,
                       confidence_level, evidence_code, created_by, created_at, updated_at,
                       uuid, approved_by_curator, approved_at_curator
                FROM ke_go_mappings
                ORDER BY created_at DESC
            """
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_mappings_by_ke(self, ke_id: str) -> List[Dict]:
        """Get all GO mappings for a specific Key Event"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, ke_id, ke_title, go_id, go_name, connection_type,
                       confidence_level, evidence_code, created_by, created_at, updated_at,
                       uuid, approved_by_curator, approved_at_curator
                FROM ke_go_mappings
                WHERE ke_id = ?
                ORDER BY created_at DESC
                """,
                (ke_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def check_mapping_exists(self, ke_id: str, go_id: str) -> Dict:
        """Check if KE-GO pair exists"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM ke_go_mappings WHERE ke_id = ? AND go_id = ?",
                (ke_id, go_id),
            )
            pair_match = cursor.fetchone()

            if pair_match:
                return {
                    "pair_exists": True,
                    "message": f"The KE-GO pair ({ke_id}, {go_id}) already exists.",
                }

            cursor = conn.execute(
                "SELECT * FROM ke_go_mappings WHERE ke_id = ?",
                (ke_id,),
            )
            ke_matches = [dict(row) for row in cursor.fetchall()]

            if ke_matches:
                return {
                    "ke_exists": True,
                    "message": f"The KE ID {ke_id} exists but not with GO ID {go_id}.",
                    "ke_matches": ke_matches,
                }

            return {
                "ke_exists": False,
                "pair_exists": False,
                "message": f"The KE ID {ke_id} and GO ID {go_id} are new entries.",
            }
        finally:
            conn.close()

    def check_go_mapping_exists_with_proposals(self, ke_id: str, go_id: str) -> Dict:
        """
        Enriched duplicate check for KE-GO pairs that returns structured blocking payloads.

        Priority order:
        1. pending_proposal — an open proposal already covers this pair (most actionable)
        2. approved_mapping — approved mapping exists, user can submit_revision
        3. ke_exists — KE exists with a different GO term (informational)
        4. nothing found

        Returns one of:
        - blocking_type='pending_proposal' if a pending proposal exists for the pair
        - blocking_type='approved_mapping' if an approved KE-GO pair exists (no pending proposal)
        - ke_exists info if the KE exists with a different GO term
        - ke_exists=False, pair_exists=False if nothing found
        """
        conn = self.db.get_connection()
        try:
            # 1. Check for pending proposal on the KE-GO pair (highest priority blocking)
            cursor = conn.execute(
                """
                SELECT p.id, p.proposed_confidence, p.proposed_connection_type,
                       p.github_username, p.created_at,
                       m.ke_id, m.go_id, m.ke_title, m.go_name
                FROM ke_go_proposals p
                JOIN ke_go_mappings m ON p.mapping_id = m.id
                WHERE m.ke_id = ? AND m.go_id = ? AND p.status = 'pending'
                ORDER BY p.created_at DESC LIMIT 1
                """,
                (ke_id, go_id),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "pair_exists": True,
                    "blocking_type": "pending_proposal",
                    "existing": {
                        "proposal_id": row["id"],
                        "ke_id": row["ke_id"],
                        "go_id": row["go_id"],
                        "ke_title": row["ke_title"],
                        "go_name": row["go_name"],
                        "proposed_confidence": row["proposed_confidence"],
                        "proposed_connection_type": row["proposed_connection_type"],
                        "submitted_by": row["github_username"],
                        "submitted_at": row["created_at"],
                    },
                    "actions": ["flag_stale"],
                }

            # 2. Check for approved mapping (exact ke_id + go_id pair)
            cursor = conn.execute(
                """
                SELECT id, ke_id, ke_title, go_id, go_name, connection_type,
                       confidence_level, approved_by_curator, approved_at_curator, uuid
                FROM ke_go_mappings WHERE ke_id = ? AND go_id = ?
                """,
                (ke_id, go_id),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "pair_exists": True,
                    "blocking_type": "approved_mapping",
                    "existing": {
                        "ke_id": row["ke_id"],
                        "go_id": row["go_id"],
                        "ke_title": row["ke_title"],
                        "go_name": row["go_name"],
                        "confidence_level": row["confidence_level"],
                        "connection_type": row["connection_type"],
                        "approved_by_curator": row["approved_by_curator"],
                        "approved_at_curator": row["approved_at_curator"],
                        "uuid": row["uuid"],
                        "id": row["id"],
                    },
                    "actions": ["submit_revision"],
                }

            # 3. Check if KE exists with a different GO term (backward-compat ke_exists path)
            cursor = conn.execute(
                "SELECT * FROM ke_go_mappings WHERE ke_id = ?",
                (ke_id,),
            )
            ke_matches = [dict(row) for row in cursor.fetchall()]
            if ke_matches:
                return {
                    "ke_exists": True,
                    "message": f"The KE ID {ke_id} exists but not with GO ID {go_id}.",
                    "ke_matches": ke_matches,
                }

            return {
                "ke_exists": False,
                "pair_exists": False,
                "message": f"The KE ID {ke_id} and GO ID {go_id} are new entries.",
            }
        finally:
            conn.close()


    def get_go_mapping_by_uuid(self, mapping_uuid: str) -> Optional[Dict]:
        """Get a GO mapping by its stable UUID"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, ke_id, ke_title, go_id, go_name, connection_type,
                       confidence_level, evidence_code, created_by, created_at, updated_at,
                       uuid, approved_by_curator, approved_at_curator
                FROM ke_go_mappings
                WHERE uuid = ?
                """,
                (mapping_uuid,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_go_mappings_paginated(
        self,
        page: int = 1,
        per_page: int = 50,
        ke_id: str = None,
        go_term_id: str = None,
        confidence_level: str = None,
    ) -> tuple:
        """
        Return (List[Dict], total_count) for approved KE-GO mappings.

        Filters (all optional, combinable):
          ke_id            — exact match on ke_go_mappings.ke_id
          go_term_id       — exact match on ke_go_mappings.go_id
          confidence_level — case-insensitive match on ke_go_mappings.confidence_level

        Returns rows with columns:
          uuid, ke_id, ke_title, go_id, go_name, go_namespace,
          confidence_level, approved_by_curator, approved_at_curator, suggestion_score
        Ordered by created_at DESC.
        """
        conditions = []
        params = []

        if ke_id:
            conditions.append("ke_id = ?")
            params.append(ke_id)
        if go_term_id:
            conditions.append("go_id = ?")
            params.append(go_term_id)
        if confidence_level:
            conditions.append("LOWER(confidence_level) = LOWER(?)")
            params.append(confidence_level)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * per_page

        conn = self.db.get_connection()
        try:
            total = conn.execute(
                f"SELECT COUNT(*) FROM ke_go_mappings {where}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"""SELECT uuid, ke_id, ke_title, go_id, go_name, go_namespace,
                           confidence_level, approved_by_curator, approved_at_curator, suggestion_score
                    FROM ke_go_mappings {where}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?""",
                params + [per_page, offset],
            ).fetchall()
            return [dict(r) for r in rows], total
        finally:
            conn.close()


class GoProposalModel:
    def __init__(self, db: Database):
        self.db = db

    def create_proposal(
        self,
        mapping_id: int,
        user_name: str,
        user_email: str,
        user_affiliation: str,
        github_username: str = None,
        proposed_delete: bool = False,
        proposed_confidence: str = None,
        proposed_connection_type: str = None,
    ) -> Optional[int]:
        """Create a new GO mapping proposal"""
        proposal_uuid = str(uuid_lib.uuid4())
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO ke_go_proposals (mapping_id, user_name, user_email, user_affiliation,
                                            github_username, proposed_delete, proposed_confidence,
                                            proposed_connection_type, uuid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    mapping_id,
                    user_name,
                    user_email,
                    user_affiliation,
                    github_username,
                    proposed_delete,
                    proposed_confidence,
                    proposed_connection_type,
                    proposal_uuid,
                ),
            )

            conn.commit()
            logger.info(
                "Created GO proposal for mapping %s by %s, UUID=%s",
                mapping_id,
                github_username,
                proposal_uuid,
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error("Error creating GO proposal: %s", e)
            conn.rollback()
            return None
        finally:
            conn.close()

    def flag_go_proposal_stale(self, proposal_id: int, flagged_by: str) -> bool:
        """
        Flag a pending GO proposal as stale for admin review.

        Args:
            proposal_id: ID of the GO proposal to flag
            flagged_by: Username of curator flagging the proposal

        Returns:
            True if successful, False otherwise
        """
        conn = self.db.get_connection()
        try:
            conn.execute(
                "UPDATE ke_go_proposals SET is_stale = 1 WHERE id = ?",
                (proposal_id,),
            )
            conn.commit()
            logger.info(
                "GO proposal %s flagged as stale by %s", proposal_id, flagged_by
            )
            return True
        except Exception as e:
            logger.error("Error flagging GO proposal %s as stale: %s", proposal_id, e)
            conn.rollback()
            return False
        finally:
            conn.close()

    def find_mapping_by_details(self, ke_id: str, go_id: str) -> Optional[int]:
        """Find GO mapping ID by KE and GO IDs"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT id FROM ke_go_mappings WHERE ke_id = ? AND go_id = ?",
                (ke_id, go_id),
            )
            row = cursor.fetchone()
            return row["id"] if row else None
        finally:
            conn.close()


class CacheModel:
    def __init__(self, db: Database):
        self.db = db

    def get_cached_response(self, endpoint: str, query_hash: str) -> Optional[str]:
        """Get cached SPARQL response if valid"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT response_data FROM sparql_cache 
                WHERE endpoint = ? AND query_hash = ? AND expires_at > CURRENT_TIMESTAMP
            """,
                (endpoint, query_hash),
            )

            row = cursor.fetchone()
            return row["response_data"] if row else None
        finally:
            conn.close()

    def cache_response(
        self, endpoint: str, query_hash: str, response_data: str, expiry_hours: int = 24
    ) -> bool:
        """Cache SPARQL response"""
        # Validate expiry_hours to prevent SQL injection
        if (
            not isinstance(expiry_hours, int) or expiry_hours < 1 or expiry_hours > 168
        ):  # Max 1 week
            expiry_hours = 24

        conn = self.db.get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO sparql_cache (endpoint, query_hash, response_data, expires_at)
                VALUES (?, ?, ?, datetime('now', '+' || ? || ' hours'))
            """,
                (endpoint, query_hash, response_data, str(expiry_hours)),
            )

            conn.commit()
            return True
        except Exception as e:
            logger.error("Error caching response: %s", e)
            return False
        finally:
            conn.close()

    def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                DELETE FROM sparql_cache WHERE expires_at <= CURRENT_TIMESTAMP
            """
            )
            deleted_count = cursor.rowcount
            conn.commit()
            if deleted_count > 0:
                logger.info("Cleaned up %d expired cache entries", deleted_count)
        except Exception as e:
            logger.error("Error cleaning cache: %s", e)
        finally:
            conn.close()


class GuestCodeModel:
    def __init__(self, db: Database):
        self.db = db

    def create_code(
        self, label: str, created_by: str, expires_at: str, max_uses: int = 1
    ) -> Optional[str]:
        """
        Create a new guest access code

        Args:
            label: Descriptive label for this code (e.g. 'workshop-2025')
            created_by: Admin username who created the code
            expires_at: ISO timestamp when the code expires
            max_uses: Maximum number of times the code can be used

        Returns:
            The generated code string, or None on failure
        """
        code = secrets.token_urlsafe(6)
        conn = self.db.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO guest_codes (code, label, created_by, expires_at, max_uses)
                VALUES (?, ?, ?, ?, ?)
            """,
                (code, label, created_by, expires_at, max_uses),
            )
            conn.commit()
            logger.info(
                "Created guest code for label=%s by %s (max_uses=%d)",
                label,
                created_by,
                max_uses,
            )
            return code
        except sqlite3.IntegrityError:
            logger.warning("Duplicate guest code generated, retrying")
            conn.rollback()
            # Retry once with a new code
            code = secrets.token_urlsafe(6)
            try:
                conn.execute(
                    """
                    INSERT INTO guest_codes (code, label, created_by, expires_at, max_uses)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (code, label, created_by, expires_at, max_uses),
                )
                conn.commit()
                return code
            except Exception:
                conn.rollback()
                return None
        except Exception as e:
            logger.error("Error creating guest code: %s", e)
            conn.rollback()
            return None
        finally:
            conn.close()

    def validate_code(self, code: str) -> Optional[Dict]:
        """
        Validate a guest access code and increment its use count

        Args:
            code: The access code to validate

        Returns:
            Dict with code details if valid, None if invalid/expired/revoked/exhausted
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, code, label, expires_at, max_uses, use_count, is_revoked
                FROM guest_codes
                WHERE code = ?
            """,
                (code,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            row_dict = dict(row)

            # Check revoked
            if row_dict["is_revoked"]:
                return None

            # Check expired
            try:
                expires = datetime.fromisoformat(row_dict["expires_at"])
                if expires < datetime.utcnow():
                    return None
            except (ValueError, TypeError):
                return None

            # Check usage limit
            if row_dict["use_count"] >= row_dict["max_uses"]:
                return None

            # Increment use count
            conn.execute(
                "UPDATE guest_codes SET use_count = use_count + 1 WHERE id = ?",
                (row_dict["id"],),
            )
            conn.commit()

            logger.info("Guest code validated for label=%s", row_dict["label"])
            return row_dict

        except Exception as e:
            logger.error("Error validating guest code: %s", e)
            conn.rollback()
            return None
        finally:
            conn.close()

    def get_all_codes(self) -> List[Dict]:
        """
        Get all guest codes with computed status

        Returns:
            List of code dicts with added 'status' field
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, code, label, created_by, created_at, expires_at,
                       max_uses, use_count, is_revoked, revoked_at, revoked_by
                FROM guest_codes
                ORDER BY created_at DESC
            """
            )
            codes = [dict(row) for row in cursor.fetchall()]

            now = datetime.utcnow()
            for code in codes:
                if code["is_revoked"]:
                    code["status"] = "revoked"
                elif code["use_count"] >= code["max_uses"]:
                    code["status"] = "exhausted"
                else:
                    try:
                        expires = datetime.fromisoformat(code["expires_at"])
                        code["status"] = "expired" if expires < now else "active"
                    except (ValueError, TypeError):
                        code["status"] = "unknown"

            return codes
        finally:
            conn.close()

    def revoke_code(self, code_id: int, revoked_by: str) -> bool:
        """
        Revoke a guest code

        Args:
            code_id: Database ID of the code to revoke
            revoked_by: Admin username revoking the code

        Returns:
            True if successful
        """
        conn = self.db.get_connection()
        try:
            conn.execute(
                """
                UPDATE guest_codes
                SET is_revoked = TRUE, revoked_at = CURRENT_TIMESTAMP, revoked_by = ?
                WHERE id = ?
            """,
                (revoked_by, code_id),
            )
            conn.commit()
            logger.info("Guest code %d revoked by %s", code_id, revoked_by)
            return True
        except Exception as e:
            logger.error("Error revoking guest code: %s", e)
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_code(self, code_id: int) -> bool:
        """
        Delete a guest code

        Args:
            code_id: Database ID of the code to delete

        Returns:
            True if successful
        """
        conn = self.db.get_connection()
        try:
            conn.execute("DELETE FROM guest_codes WHERE id = ?", (code_id,))
            conn.commit()
            logger.info("Guest code %d deleted", code_id)
            return True
        except Exception as e:
            logger.error("Error deleting guest code: %s", e)
            conn.rollback()
            return False
        finally:
            conn.close()
