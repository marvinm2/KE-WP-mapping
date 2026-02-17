"""
Rate limiting functionality for API endpoints
"""
import logging
import sqlite3
import time
from collections import defaultdict
from functools import wraps

from flask import g, jsonify, request
from src.utils.text import sanitize_log

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, db_path: str = "ke_wp_mapping.db"):
        self.db_path = db_path
        self.memory_store = defaultdict(list)  # Fallback in-memory store
        self.init_rate_limit_table()

    def init_rate_limit_table(self):
        """Initialize rate limiting table"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_ip TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    timestamp INTEGER NOT NULL
                )
            """
            )

            # Create indexes separately
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rate_limits_client_endpoint ON rate_limits(client_ip, endpoint)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rate_limits_timestamp ON rate_limits(timestamp)"
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize rate limit table: {e}")

    def is_rate_limited(
        self, client_ip: str, endpoint: str, limit: int = 100, window: int = 3600
    ) -> bool:
        """
        Check if client is rate limited
        Args:
            client_ip: Client IP address
            endpoint: API endpoint being accessed
            limit: Maximum requests allowed in window
            window: Time window in seconds (default 1 hour)
        """
        current_time = int(time.time())
        cutoff_time = current_time - window

        try:
            conn = sqlite3.connect(self.db_path)

            # Clean up old entries
            conn.execute(
                """
                DELETE FROM rate_limits WHERE timestamp < ?
            """,
                (cutoff_time,),
            )

            # Count recent requests
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM rate_limits 
                WHERE client_ip = ? AND endpoint = ? AND timestamp >= ?
            """,
                (client_ip, endpoint, cutoff_time),
            )

            count = cursor.fetchone()[0]

            # Record this request
            conn.execute(
                """
                INSERT INTO rate_limits (client_ip, endpoint, timestamp)
                VALUES (?, ?, ?)
            """,
                (client_ip, endpoint, current_time),
            )

            conn.commit()
            conn.close()

            return count >= limit

        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            # Fallback to memory-based rate limiting
            return self._memory_rate_limit(client_ip, endpoint, limit, window)

    def _memory_rate_limit(
        self, client_ip: str, endpoint: str, limit: int, window: int
    ) -> bool:
        """Fallback in-memory rate limiting"""
        key = f"{client_ip}:{endpoint}"
        current_time = time.time()

        # Clean old entries
        self.memory_store[key] = [
            timestamp
            for timestamp in self.memory_store[key]
            if current_time - timestamp < window
        ]

        # Add current request
        self.memory_store[key].append(current_time)

        return len(self.memory_store[key]) > limit


def rate_limit(limit: int = 100, window: int = 3600, per_endpoint: bool = True):
    """
    Rate limiting decorator
    Args:
        limit: Maximum requests allowed
        window: Time window in seconds
        per_endpoint: Whether to apply limit per endpoint or globally
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get rate limiter instance
            if not hasattr(g, "rate_limiter"):
                g.rate_limiter = RateLimiter()

            client_ip = request.environ.get(
                "HTTP_X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR", "unknown")
            )

            endpoint = request.endpoint if per_endpoint else "global"

            if g.rate_limiter.is_rate_limited(client_ip, endpoint, limit, window):
                logger.warning("Rate limit exceeded for %s on %s", sanitize_log(client_ip), sanitize_log(endpoint))
                return (
                    jsonify(
                        {
                            "error": "Rate limit exceeded. Please try again later.",
                            "limit": limit,
                            "window": window,
                        }
                    ),
                    429,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Specific rate limit decorators for different use cases
def sparql_rate_limit(f):
    """Rate limit for SPARQL endpoints (increased for development)"""
    return rate_limit(limit=500, window=3600)(f)


def submission_rate_limit(f):
    """Rate limit for data submission endpoints"""
    return rate_limit(limit=20, window=3600)(f)


def general_rate_limit(f):
    """General rate limit for other endpoints"""
    return rate_limit(limit=1000, window=3600)(f)
