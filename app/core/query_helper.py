"""
Query Helper Utilities

Centralizes common database query patterns to reduce code duplication
across API endpoints and services.
"""

from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session


class QueryHelper:
    """
    Helper class for common database query patterns.

    Reduces repetitive filtering, pagination, and querying logic
    throughout the application.
    """

    @staticmethod
    def apply_filters(
        query: Query,
        model: type,
        filters: dict[str, Any]
    ) -> Query:
        """
        Apply multiple filters to a query.

        Args:
            query: SQLAlchemy query object
            model: Model class
            filters: Dictionary of field_name: value pairs

        Returns:
            Filtered query
        """
        for key, value in filters.items():
            if value is not None and hasattr(model, key):
                if isinstance(value, list):
                    query = query.filter(getattr(model, key).in_(value))
                else:
                    query = query.filter(getattr(model, key) == value)
        return query

    @staticmethod
    def paginated_query(
        model: type,
        db: Session,
        page: int = 1,
        limit: int = 20,
        **filters
    ) -> tuple[list[Any], int]:
        """
        Execute a paginated query with filters.

        Args:
            model: SQLAlchemy model class
            db: Database session
            page: Page number (1-indexed)
            limit: Items per page
            **filters: Filter criteria

        Returns:
            Tuple of (items, total_count)
        """
        query = db.query(model)
        query = QueryHelper.apply_filters(query, model, filters)

        total = query.count()
        skip = (page - 1) * limit
        items = query.offset(skip).limit(limit).all()

        return items, total

    @staticmethod
    def search_across_fields(
        query: Query,
        model: type,
        search_term: str,
        search_fields: list[str]
    ) -> Query:
        """
        Search across multiple fields using ILIKE.

        Args:
            query: SQLAlchemy query
            model: Model class
            search_term: Search string
            search_fields: List of field names to search

        Returns:
            Query with search filters applied
        """
        if not search_term:
            return query

        search_conditions = []
        for field in search_fields:
            if hasattr(model, field):
                search_conditions.append(
                    getattr(model, field).ilike(f'%{search_term}%')
                )

        if search_conditions:
            query = query.filter(or_(*search_conditions))

        return query

    @staticmethod
    def get_or_none(
        model: type,
        db: Session,
        **filters
    ) -> Any | None:
        """
        Get a single record or return None.

        Args:
            model: SQLAlchemy model class
            db: Database session
            **filters: Filter criteria

        Returns:
            Model instance or None
        """
        query = db.query(model)
        query = QueryHelper.apply_filters(query, model, filters)
        return query.first()

    @staticmethod
    def count_with_filters(
        model: type,
        db: Session,
        **filters
    ) -> int:
        """
        Count records matching filters.

        Args:
            model: SQLAlchemy model class
            db: Database session
            **filters: Filter criteria

        Returns:
            Count of matching records
        """
        query = db.query(func.count(model.id))
        query = QueryHelper.apply_filters(query, model, filters)
        return query.scalar()

    @staticmethod
    def exists(
        model: type,
        db: Session,
        **filters
    ) -> bool:
        """
        Check if any record exists matching filters.

        Args:
            model: SQLAlchemy model class
            db: Database session
            **filters: Filter criteria

        Returns:
            True if exists, False otherwise
        """
        query = db.query(model.id)
        query = QueryHelper.apply_filters(query, model, filters)
        return query.first() is not None
