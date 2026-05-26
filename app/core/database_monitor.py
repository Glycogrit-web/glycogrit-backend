"""
Database Health Monitoring
Provides utilities to monitor database health, performance, and connection status
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.core.database import SessionLocal, engine

logger = logging.getLogger(__name__)


class DatabaseMonitor:
    """
    Database monitoring and health check utilities

    Follows the Single Responsibility Principle - focused only on monitoring
    """

    @staticmethod
    def check_connection() -> dict[str, Any]:
        """
        Test database connection

        Returns:
            Dict with connection status and details
        """
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

                return {
                    "status": "healthy",
                    "connected": True,
                    "message": "Database connection successful",
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    @staticmethod
    def get_connection_pool_stats() -> dict[str, Any]:
        """
        Get connection pool statistics

        Returns:
            Dict with pool size, connections in use, etc.
        """
        try:
            pool = engine.pool

            return {
                "pool_size": pool.size(),
                "checked_out_connections": pool.checkedout(),
                "overflow_connections": pool.overflow(),
                "total_connections": pool.size() + pool.overflow(),
                "status": "healthy" if pool.checkedout() < pool.size() else "warning",
            }
        except Exception as e:
            logger.error(f"Failed to get pool stats: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_database_size() -> dict[str, Any]:
        """
        Get database size information

        Returns:
            Dict with database size metrics
        """
        try:
            db = SessionLocal()
            try:
                # Get database size
                result = db.execute(
                    text("SELECT pg_size_pretty(pg_database_size(current_database())) as size")
                )
                db_size = result.fetchone()[0]

                # Get total table count
                result = db.execute(
                    text("SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'")
                )
                table_count = result.fetchone()[0]

                # Get total rows
                result = db.execute(
                    text("SELECT COALESCE(SUM(n_live_tup), 0) FROM pg_stat_user_tables")
                )
                total_rows = result.fetchone()[0]

                return {
                    "database_size": db_size,
                    "table_count": table_count,
                    "total_rows": total_rows,
                    "status": "healthy",
                }
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_table_sizes() -> list[dict[str, Any]]:
        """
        Get size information for all tables

        Returns:
            List of dicts with table names and sizes
        """
        try:
            db = SessionLocal()
            try:
                result = db.execute(text("""
                    SELECT
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                        pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 20
                """))

                tables = []
                for row in result:
                    tables.append(
                        {"schema": row[0], "table": row[1], "size": row[2], "size_bytes": row[3]}
                    )

                return tables
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to get table sizes: {e}")
            return []

    @staticmethod
    def get_slow_queries(limit: int = 10) -> list[dict[str, Any]]:
        """
        Get slow running queries (requires pg_stat_statements extension)

        Args:
            limit: Number of queries to return

        Returns:
            List of slow queries with statistics
        """
        try:
            db = SessionLocal()
            try:
                # Check if pg_stat_statements is available
                result = db.execute(
                    text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'pg_stat_statements'")
                )
                if result.fetchone()[0] == 0:
                    return [
                        {"status": "info", "message": "pg_stat_statements extension not installed"}
                    ]

                result = db.execute(text(f"""
                    SELECT
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        max_exec_time
                    FROM pg_stat_statements
                    ORDER BY mean_exec_time DESC
                    LIMIT {limit}
                """))

                queries = []
                for row in result:
                    queries.append(
                        {
                            "query": row[0][:200],  # Truncate long queries
                            "calls": row[1],
                            "total_time_ms": round(row[2], 2),
                            "mean_time_ms": round(row[3], 2),
                            "max_time_ms": round(row[4], 2),
                        }
                    )

                return queries
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to get slow queries: {e}")
            return [{"status": "error", "message": str(e)}]

    @staticmethod
    def get_active_connections() -> dict[str, Any]:
        """
        Get information about active database connections

        Returns:
            Dict with connection statistics
        """
        try:
            db = SessionLocal()
            try:
                result = db.execute(text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE state = 'active') as active,
                        COUNT(*) FILTER (WHERE state = 'idle') as idle,
                        COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """))

                row = result.fetchone()
                return {
                    "total_connections": row[0],
                    "active": row[1],
                    "idle": row[2],
                    "idle_in_transaction": row[3],
                    "status": "healthy" if row[3] == 0 else "warning",
                }
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to get active connections: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_index_usage() -> list[dict[str, Any]]:
        """
        Get index usage statistics to identify unused indexes

        Returns:
            List of indexes with usage statistics
        """
        try:
            db = SessionLocal()
            try:
                result = db.execute(text("""
                    SELECT
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch,
                        pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                    ORDER BY idx_scan ASC
                    LIMIT 20
                """))

                indexes = []
                for row in result:
                    indexes.append(
                        {
                            "schema": row[0],
                            "table": row[1],
                            "index": row[2],
                            "scans": row[3],
                            "tuples_read": row[4],
                            "tuples_fetched": row[5],
                            "size": row[6],
                            "status": "unused" if row[3] == 0 else "used",
                        }
                    )

                return indexes
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to get index usage: {e}")
            return []

    @staticmethod
    def get_full_health_report() -> dict[str, Any]:
        """
        Get comprehensive database health report

        Returns:
            Complete health report with all metrics
        """
        logger.info("Generating database health report...")

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "connection": DatabaseMonitor.check_connection(),
            "pool": DatabaseMonitor.get_connection_pool_stats(),
            "database": DatabaseMonitor.get_database_size(),
            "connections": DatabaseMonitor.get_active_connections(),
            "largest_tables": DatabaseMonitor.get_table_sizes(),
            "index_usage": DatabaseMonitor.get_index_usage(),
        }

        # Determine overall status
        statuses = [
            report["connection"].get("status"),
            report["pool"].get("status"),
            report["database"].get("status"),
            report["connections"].get("status"),
        ]

        if "unhealthy" in statuses or "error" in statuses:
            report["overall_status"] = "unhealthy"
        elif "warning" in statuses:
            report["overall_status"] = "warning"
        else:
            report["overall_status"] = "healthy"

        logger.info(f"Health report generated. Overall status: {report['overall_status']}")
        return report


# Convenience function for quick health check
def quick_health_check() -> bool:
    """
    Quick health check - returns True if database is healthy

    Returns:
        True if database is accessible, False otherwise
    """
    result = DatabaseMonitor.check_connection()
    return result.get("connected", False)
