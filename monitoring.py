"""
Performance monitoring and metrics collection
"""
import functools
import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional

from flask import g, request

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self, db_path: str = "ke_wp_mapping.db"):
        self.db_path = db_path
        self.memory_metrics = defaultdict(
            lambda: {
                "requests": deque(maxlen=1000),
                "response_times": deque(maxlen=1000),
                "errors": deque(maxlen=1000),
            }
        )
        self.init_metrics_table()

    def init_metrics_table(self):
        """Initialize metrics table in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    response_time REAL NOT NULL,
                    client_ip TEXT,
                    user_agent TEXT,
                    error_message TEXT
                )
            """
            )

            # Create indexes separately
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_endpoint ON metrics(endpoint)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_status_code ON metrics(status_code)"
            )

            # Create performance summary table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    total_requests INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    cache_hits INTEGER DEFAULT 0,
                    cache_misses INTEGER DEFAULT 0,
                    UNIQUE(date, endpoint)
                )
            """
            )

            conn.commit()
            conn.close()
            logger.info("Metrics tables initialized")
        except Exception as e:
            logger.error(f"Failed to initialize metrics tables: {e}")

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        client_ip: str = None,
        user_agent: str = None,
        error_message: str = None,
    ):
        """Record a request metric"""
        timestamp = int(time.time())

        # Store in memory for quick access
        self.memory_metrics[endpoint]["requests"].append(
            {
                "timestamp": timestamp,
                "status_code": status_code,
                "response_time": response_time,
            }
        )

        if status_code >= 400:
            self.memory_metrics[endpoint]["errors"].append(
                {
                    "timestamp": timestamp,
                    "status_code": status_code,
                    "error": error_message,
                }
            )

        # Store in database (async to avoid blocking)
        threading.Thread(
            target=self._store_metric_async,
            args=(
                timestamp,
                endpoint,
                method,
                status_code,
                response_time,
                client_ip,
                user_agent,
                error_message,
            ),
        ).start()

    def _store_metric_async(
        self,
        timestamp: int,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        client_ip: str,
        user_agent: str,
        error_message: str,
    ):
        """Store metric in database asynchronously"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                INSERT INTO metrics (timestamp, endpoint, method, status_code, 
                                   response_time, client_ip, user_agent, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    endpoint,
                    method,
                    status_code,
                    response_time,
                    client_ip,
                    user_agent,
                    error_message,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to store metric: {e}")

    def get_endpoint_stats(self, endpoint: str, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for a specific endpoint"""
        cutoff_time = int(time.time()) - (hours * 3600)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                """
                SELECT COUNT(*) as total_requests,
                       AVG(response_time) as avg_response_time,
                       MIN(response_time) as min_response_time,
                       MAX(response_time) as max_response_time,
                       COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count,
                       COUNT(CASE WHEN status_code = 200 THEN 1 END) as success_count
                FROM metrics 
                WHERE endpoint = ? AND timestamp >= ?
            """,
                (endpoint, cutoff_time),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "endpoint": endpoint,
                    "total_requests": row[0] or 0,
                    "avg_response_time": round(row[1] or 0, 3),
                    "min_response_time": round(row[2] or 0, 3),
                    "max_response_time": round(row[3] or 0, 3),
                    "error_count": row[4] or 0,
                    "success_count": row[5] or 0,
                    "error_rate": round((row[4] or 0) / max(row[0] or 1, 1) * 100, 2),
                    "hours": hours,
                }
        except Exception as e:
            logger.error(f"Failed to get endpoint stats: {e}")

        return {"endpoint": endpoint, "error": "Failed to fetch stats"}

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Get recent metrics (last hour)
            cutoff_time = int(time.time()) - 3600

            cursor = conn.execute(
                """
                SELECT endpoint,
                       COUNT(*) as requests,
                       AVG(response_time) as avg_response_time,
                       COUNT(CASE WHEN status_code >= 400 THEN 1 END) as errors
                FROM metrics 
                WHERE timestamp >= ?
                GROUP BY endpoint
                ORDER BY requests DESC
            """,
                (cutoff_time,),
            )

            endpoints = []
            total_requests = 0
            total_errors = 0

            for row in cursor.fetchall():
                endpoint_data = {
                    "endpoint": row[0],
                    "requests": row[1],
                    "avg_response_time": round(row[2], 3),
                    "errors": row[3],
                }
                endpoints.append(endpoint_data)
                total_requests += row[1]
                total_errors += row[3]

            # Get database size
            cursor = conn.execute(
                "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            )
            result = cursor.fetchone()
            db_size = result[0] if result else 0

            conn.close()

            return {
                "timestamp": int(time.time()),
                "total_requests_last_hour": total_requests,
                "total_errors_last_hour": total_errors,
                "error_rate_last_hour": round(
                    total_errors / max(total_requests, 1) * 100, 2
                ),
                "database_size_bytes": db_size,
                "endpoints": endpoints[:10],  # Top 10 endpoints
            }

        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {"error": "Failed to fetch system health"}


# Global metrics collector instance
metrics_collector = MetricsCollector()


def monitor_performance(f):
    """Decorator to monitor endpoint performance"""

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()

        try:
            response = f(*args, **kwargs)

            # Handle different response types
            if hasattr(response, "status_code"):
                status_code = response.status_code
            else:
                status_code = 200

            response_time = time.time() - start_time

            # Record the metric
            metrics_collector.record_request(
                endpoint=request.endpoint or "unknown",
                method=request.method,
                status_code=status_code,
                response_time=response_time,
                client_ip=request.environ.get(
                    "HTTP_X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR")
                ),
                user_agent=request.headers.get("User-Agent", ""),
            )

            return response

        except Exception as e:
            response_time = time.time() - start_time

            # Record the error
            metrics_collector.record_request(
                endpoint=request.endpoint or "unknown",
                method=request.method,
                status_code=500,
                response_time=response_time,
                client_ip=request.environ.get(
                    "HTTP_X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR")
                ),
                user_agent=request.headers.get("User-Agent", ""),
                error_message=str(e),
            )

            raise

    return decorated_function


class PerformanceProfiler:
    """Context manager for profiling code blocks"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        logger.info(f"Performance: {self.operation_name} took {duration:.3f} seconds")

        if duration > 1.0:  # Log slow operations
            logger.warning(
                f"Slow operation detected: {self.operation_name} took {duration:.3f} seconds"
            )


def log_slow_queries(threshold_seconds: float = 1.0):
    """Decorator to log slow database queries"""

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = f(*args, **kwargs)
            duration = time.time() - start_time

            if duration > threshold_seconds:
                logger.warning(f"Slow query in {f.__name__}: {duration:.3f}s")

            return result

        return wrapper

    return decorator
