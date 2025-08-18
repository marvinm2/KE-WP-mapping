"""
Database models for KE-WP Mapping Application
"""
import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "ke_wp_mapping.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get database connection with row factory for dict-like access"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
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

            # Migrate proposals table to add admin fields if needed
            self._migrate_proposals_admin_fields(conn)
            
            # Migrate mappings table to add updated_by field if needed
            self._migrate_mappings_updated_by_field(conn)

            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
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
                    f"Adding missing admin fields to proposals table: {missing_fields}"
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
            logger.error(f"Error migrating proposals table: {e}")
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
            logger.error(f"Error migrating mappings table: {e}")
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
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title, connection_type, 
                                    confidence_level, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    ke_id,
                    ke_title,
                    wp_id,
                    wp_title,
                    connection_type,
                    confidence_level,
                    created_by,
                ),
            )

            conn.commit()
            logger.info(f"Created mapping: KE={ke_id}, WP={wp_id}, User={created_by}")
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Duplicate mapping attempted: KE={ke_id}, WP={wp_id}")
            return None
        except Exception as e:
            logger.error(f"Error creating mapping: {e}")
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
                       confidence_level, created_by, created_at, updated_at
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
                       confidence_level, created_by, created_at, updated_at
                FROM mappings 
                WHERE ke_id = ?
                ORDER BY created_at DESC
                """,
                (ke_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
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

    def update_mapping(
        self,
        mapping_id: int,
        connection_type: str = None,
        confidence_level: str = None,
        updated_by: str = None,
    ) -> bool:
        """
        Update an existing mapping

        Args:
            mapping_id: ID of the mapping to update
            connection_type: New connection type (optional)
            confidence_level: New confidence level (optional)
            updated_by: Username of person making the update

        Returns:
            True if successful, False otherwise
        """
        # Define allowed fields to prevent SQL injection
        ALLOWED_FIELDS = {
            "connection_type": "connection_type",
            "confidence_level": "confidence_level",
            "updated_by": "updated_by",
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
            logger.info(f"Updated mapping {mapping_id} by {updated_by}")
            return True
        except Exception as e:
            logger.error(f"Error updating mapping: {e}")
            conn.rollback()
            return False
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
            logger.info(f"Deleted mapping {mapping_id} by {deleted_by}")
            return True
        except Exception as e:
            logger.error(f"Error deleting mapping: {e}")
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
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO proposals (mapping_id, user_name, user_email, user_affiliation,
                                     github_username, proposed_delete, proposed_confidence,
                                     proposed_connection_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )

            conn.commit()
            logger.info(
                f"Created proposal for mapping {mapping_id} by {github_username}"
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating proposal: {e}")
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
            logger.error(f"Invalid status value: {status}")
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
                f"Updated proposal {proposal_id} to {status} by {admin_username}"
            )
            return True
        except Exception as e:
            logger.error(f"Error updating proposal status: {e}")
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
            logger.error(f"Error caching response: {e}")
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
                logger.info(f"Cleaned up {deleted_count} expired cache entries")
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")
        finally:
            conn.close()
