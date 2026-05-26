"""
Health Check System

Provides comprehensive health checks for monitoring and observability:
- Database connectivity and pool status
- Application uptime and version info
- System resource metrics
- Dependency status checks

Used by:
- Load balancers for routing decisions
- Monitoring systems (Datadog, New Relic, etc.)
- Kubernetes liveness/readiness probes
- Railway health checks
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import psutil
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status values"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Working but with issues
    UNHEALTHY = "unhealthy"  # Critical failure


class HealthCheck:
    """
    Comprehensive health check system for the application.

    Performs checks on:
    - Database connectivity and query performance
    - Database connection pool status
    - System resources (CPU, memory, disk)
    - Application uptime
    """

    # Track application start time
    _start_time: datetime = datetime.utcnow()

    @classmethod
    def get_uptime(cls) -> dict[str, Any]:
        """
        Get application uptime information.

        Returns:
            Dict with uptime in seconds and human-readable format
        """
        uptime_delta: timedelta = datetime.utcnow() - cls._start_time
        uptime_seconds: int = int(uptime_delta.total_seconds())

        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60

        uptime_human = f"{days}d {hours}h {minutes}m {seconds}s"

        return {
            "started_at": cls._start_time.isoformat(),
            "uptime_seconds": uptime_seconds,
            "uptime_human": uptime_human,
        }

    @staticmethod
    def check_database(db: Session, engine: Engine) -> dict[str, Any]:
        """
        Check database connectivity, query performance, and connection pool status.

        Args:
            db: SQLAlchemy database session
            engine: SQLAlchemy engine for pool inspection

        Returns:
            Dict with database health metrics and status
        """
        start_time = datetime.utcnow()

        try:
            # Execute a simple query to test connectivity
            result = db.execute(text("SELECT 1 as health_check"))
            result.fetchone()

            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # Convert to ms

            # Get connection pool statistics
            pool = engine.pool
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "max_overflow": pool._max_overflow if hasattr(pool, "_max_overflow") else None,
            }

            # Determine status based on query time and pool usage
            if query_time > 1000:  # > 1 second is concerning
                status = HealthStatus.DEGRADED
                message = f"Database responding slowly ({query_time:.2f}ms)"
            elif pool.checkedout() > pool.size() * 0.8:  # > 80% pool usage
                status = HealthStatus.DEGRADED
                message = f"High connection pool usage ({pool.checkedout()}/{pool.size()})"
            else:
                status = HealthStatus.HEALTHY
                message = "Database connection healthy"

            return {
                "status": status,
                "message": message,
                "connected": True,
                "query_time_ms": round(query_time, 2),
                "pool": pool_status,
            }

        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Database connection failed: {str(e)}",
                "connected": False,
                "error": str(e),
            }

    @staticmethod
    def get_system_resources() -> dict[str, Any]:
        """
        Get system resource metrics (CPU, memory, disk).

        Returns:
            Dict with system resource usage
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_info = {
                "total_mb": round(memory.total / 1024 / 1024, 2),
                "available_mb": round(memory.available / 1024 / 1024, 2),
                "used_mb": round(memory.used / 1024 / 1024, 2),
                "percent": memory.percent,
            }

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_info = {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "percent": disk.percent,
            }

            # Determine resource status
            status = HealthStatus.HEALTHY
            warnings: list[str] = []

            if cpu_percent > 80:
                status = HealthStatus.DEGRADED
                warnings.append(f"High CPU usage: {cpu_percent}%")

            if memory.percent > 80:
                status = HealthStatus.DEGRADED
                warnings.append(f"High memory usage: {memory.percent}%")

            if disk.percent > 80:
                status = HealthStatus.DEGRADED
                warnings.append(f"High disk usage: {disk.percent}%")

            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory": memory_info,
                "disk": disk_info,
                "warnings": warnings if warnings else None,
            }

        except Exception as e:
            logger.error(f"System resource check failed: {str(e)}")
            return {
                "status": HealthStatus.DEGRADED,
                "message": f"Could not fetch system metrics: {str(e)}",
                "error": str(e),
            }

    @classmethod
    def full_health_check(
        cls, db: Session, engine: Engine, include_resources: bool = True
    ) -> dict[str, Any]:
        """
        Perform a complete health check of all application components.

        Args:
            db: SQLAlchemy database session
            engine: SQLAlchemy engine
            include_resources: Whether to include system resource metrics

        Returns:
            Dict with complete health check results and overall status
        """
        checks: dict[str, Any] = {}

        # Database check (always included)
        checks["database"] = cls.check_database(db, engine)

        # System resources check (optional, can be heavy)
        if include_resources:
            checks["resources"] = cls.get_system_resources()

        # Uptime info
        checks["uptime"] = cls.get_uptime()

        # Determine overall health status
        statuses = [
            checks["database"]["status"],
            checks.get("resources", {}).get("status", HealthStatus.HEALTHY),
        ]

        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        }

    @classmethod
    def simple_health_check(cls) -> dict[str, Any]:
        """
        Simple health check for load balancers (no DB connection required).

        Returns:
            Dict with basic health status
        """
        uptime = cls.get_uptime()

        return {
            "status": HealthStatus.HEALTHY,
            "message": "Application is running",
            "uptime_seconds": uptime["uptime_seconds"],
            "timestamp": datetime.utcnow().isoformat(),
        }


# Export commonly used components
__all__ = [
    "HealthCheck",
    "HealthStatus",
]
