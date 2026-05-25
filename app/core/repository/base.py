"""
Base repository with generic CRUD operations.

All entity-specific repositories should inherit from BaseRepository
to get standard database operations for free.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Query, Session

from app.core.exceptions import DatabaseException

# Generic type for SQLAlchemy models
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository providing standard CRUD operations.

    Type Parameters:
        ModelType: The SQLAlchemy model class this repository manages
    """

    def __init__(self, model: type[ModelType], db: Session):
        """
        Initialize the repository.

        Args:
            model: The SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def create(self, data: dict[str, Any]) -> ModelType:
        """
        Create a new record in the database.

        Args:
            data: Dictionary of field names and values

        Returns:
            The created model instance

        Raises:
            DatabaseException: If the database operation fails
        """
        try:
            instance = self.model(**data)
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(f"Failed to create {self.model.__name__}: {str(e)}")

    def get_by_id(self, id: int) -> ModelType | None:
        """
        Retrieve a record by its ID.

        Args:
            id: The record ID

        Returns:
            The model instance if found, None otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """
        Retrieve all records with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def update(self, id: int, data: dict[str, Any]) -> ModelType | None:
        """
        Update a record by its ID.

        Args:
            id: The record ID
            data: Dictionary of field names and values to update

        Returns:
            The updated model instance if found, None otherwise

        Raises:
            DatabaseException: If the database operation fails
        """
        try:
            instance = self.get_by_id(id)
            if instance:
                for key, value in data.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                self.db.commit()
                self.db.refresh(instance)
            return instance
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(f"Failed to update {self.model.__name__}: {str(e)}")

    def delete(self, id: int) -> bool:
        """
        Delete a record by its ID.

        Args:
            id: The record ID

        Returns:
            True if the record was deleted, False if not found

        Raises:
            DatabaseException: If the database operation fails
        """
        try:
            instance = self.get_by_id(id)
            if instance:
                self.db.delete(instance)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(f"Failed to delete {self.model.__name__}: {str(e)}")

    def exists(self, id: int) -> bool:
        """
        Check if a record exists by its ID.

        Args:
            id: The record ID

        Returns:
            True if the record exists, False otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).count() > 0

    def count(self, **filters) -> int:
        """
        Count records matching the given filters.

        Args:
            **filters: Field name and value pairs to filter by

        Returns:
            Number of matching records
        """
        query = self.db.query(func.count(self.model.id))
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.scalar()

    def find_by(self, **filters) -> list[ModelType]:
        """
        Find all records matching the given filters.

        Args:
            **filters: Field name and value pairs to filter by

        Returns:
            List of matching model instances
        """
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.all()

    def find_one_by(self, **filters) -> ModelType | None:
        """
        Find a single record matching the given filters.

        Args:
            **filters: Field name and value pairs to filter by

        Returns:
            The first matching model instance, or None if not found
        """
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.first()

    # ==================== Query Builder Methods ====================

    def query(self) -> 'QueryBuilder[ModelType]':
        """
        Get a QueryBuilder instance for fluent query construction

        Usage:
            repo.query() \\
                .filter_by(is_active=True) \\
                .order_by('created_at', 'desc') \\
                .paginate(page=1, size=20) \\
                .all()

        Returns:
            QueryBuilder instance
        """
        return QueryBuilder(self.model, self.db)

    def filter_active(self, is_active: bool = True) -> list[ModelType]:
        """
        Quick filter for active/inactive records

        Args:
            is_active: Active status to filter by

        Returns:
            List of matching records
        """
        if hasattr(self.model, 'is_active'):
            return self.find_by(is_active=is_active)
        return self.get_all()

    def get_recent(self, limit: int = 10, order_by: str = 'created_at') -> list[ModelType]:
        """
        Get most recent records

        Args:
            limit: Maximum number of records
            order_by: Field to order by (default: created_at)

        Returns:
            List of recent records
        """
        query = self.db.query(self.model)
        if hasattr(self.model, order_by):
            query = query.order_by(desc(getattr(self.model, order_by)))
        return query.limit(limit).all()

    def bulk_create(self, data_list: list[dict[str, Any]]) -> list[ModelType]:
        """
        Create multiple records in one transaction

        Args:
            data_list: List of dictionaries with field data

        Returns:
            List of created instances

        Raises:
            DatabaseException: If the bulk operation fails
        """
        try:
            instances = [self.model(**data) for data in data_list]
            self.db.add_all(instances)
            self.db.commit()
            for instance in instances:
                self.db.refresh(instance)
            return instances
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(f"Failed to bulk create {self.model.__name__}: {str(e)}")

    def bulk_update(self, updates: list[tuple[int, dict[str, Any]]]) -> int:
        """
        Update multiple records in one transaction

        Args:
            updates: List of tuples (id, data_dict)

        Returns:
            Number of records updated

        Raises:
            DatabaseException: If the bulk operation fails
        """
        try:
            count = 0
            for record_id, data in updates:
                instance = self.get_by_id(record_id)
                if instance:
                    for key, value in data.items():
                        if hasattr(instance, key):
                            setattr(instance, key, value)
                    count += 1
            self.db.commit()
            return count
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(f"Failed to bulk update {self.model.__name__}: {str(e)}")

    def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        **filters
    ) -> tuple[list[ModelType], int]:
        """
        Get paginated results with total count

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            **filters: Optional filters to apply

        Returns:
            Tuple of (items, total_count)
        """
        query = self.db.query(self.model)

        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        # Get total count
        total = query.count()

        # Get paginated items
        skip = (page - 1) * page_size
        items = query.offset(skip).limit(page_size).all()

        return items, total


class QueryBuilder(Generic[ModelType]):
    """
    Fluent query builder for complex queries
    Allows chaining query operations for cleaner code

    Usage:
        results = QueryBuilder(User, db) \\
            .filter_by(role='user') \\
            .filter_active() \\
            .search('john', ['first_name', 'last_name', 'email']) \\
            .order_by('created_at', 'desc') \\
            .with_relationships('registrations', 'activities') \\
            .paginate(page=1, size=20) \\
            .all()
    """

    def __init__(self, model: type[ModelType], db: Session):
        self.model = model
        self.db = db
        self._query: Query = db.query(model)
        self._page: int | None = None
        self._page_size: int | None = None

    def filter_by(self, **filters) -> 'QueryBuilder[ModelType]':
        """
        Add equality filters

        Args:
            **filters: Field name and value pairs

        Returns:
            Self for chaining
        """
        for key, value in filters.items():
            if hasattr(self.model, key):
                self._query = self._query.filter(getattr(self.model, key) == value)
        return self

    def filter_not(self, **filters) -> 'QueryBuilder[ModelType]':
        """
        Add inequality filters

        Args:
            **filters: Field name and value pairs to exclude

        Returns:
            Self for chaining
        """
        for key, value in filters.items():
            if hasattr(self.model, key):
                self._query = self._query.filter(getattr(self.model, key) != value)
        return self

    def filter_in(self, field: str, values: list[Any]) -> 'QueryBuilder[ModelType]':
        """
        Add IN filter

        Args:
            field: Field name
            values: List of values

        Returns:
            Self for chaining
        """
        if hasattr(self.model, field):
            self._query = self._query.filter(getattr(self.model, field).in_(values))
        return self

    def filter_active(self, is_active: bool = True) -> 'QueryBuilder[ModelType]':
        """
        Filter by active status

        Args:
            is_active: Active status

        Returns:
            Self for chaining
        """
        if hasattr(self.model, 'is_active'):
            self._query = self._query.filter(self.model.is_active == is_active)
        return self

    def filter_date_range(
        self,
        field: str,
        start: datetime | None = None,
        end: datetime | None = None
    ) -> 'QueryBuilder[ModelType]':
        """
        Filter by date range

        Args:
            field: Date field name
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            Self for chaining
        """
        if hasattr(self.model, field):
            field_attr = getattr(self.model, field)
            if start:
                self._query = self._query.filter(field_attr >= start)
            if end:
                self._query = self._query.filter(field_attr <= end)
        return self

    def search(self, term: str, fields: list[str]) -> 'QueryBuilder[ModelType]':
        """
        Search across multiple fields using LIKE

        Args:
            term: Search term
            fields: List of field names to search

        Returns:
            Self for chaining
        """
        if not term:
            return self

        search_filters = []
        for field in fields:
            if hasattr(self.model, field):
                search_filters.append(
                    getattr(self.model, field).ilike(f'%{term}%')
                )

        if search_filters:
            self._query = self._query.filter(or_(*search_filters))

        return self

    def order_by(self, field: str, direction: str = 'asc') -> 'QueryBuilder[ModelType]':
        """
        Add ordering

        Args:
            field: Field name to order by
            direction: 'asc' or 'desc'

        Returns:
            Self for chaining
        """
        if hasattr(self.model, field):
            field_attr = getattr(self.model, field)
            if direction.lower() == 'desc':
                self._query = self._query.order_by(desc(field_attr))
            else:
                self._query = self._query.order_by(asc(field_attr))
        return self

    def order_by_recent(self, field: str = 'created_at') -> 'QueryBuilder[ModelType]':
        """
        Order by most recent (descending)

        Args:
            field: Date field to order by

        Returns:
            Self for chaining
        """
        return self.order_by(field, 'desc')

    def with_relationships(self, *relationships) -> 'QueryBuilder[ModelType]':
        """
        Eager load relationships

        Args:
            *relationships: Relationship names to load

        Returns:
            Self for chaining
        """
        from sqlalchemy.orm import joinedload

        for rel in relationships:
            if hasattr(self.model, rel):
                self._query = self._query.options(joinedload(getattr(self.model, rel)))

        return self

    def limit(self, limit: int) -> 'QueryBuilder[ModelType]':
        """
        Add limit

        Args:
            limit: Maximum number of results

        Returns:
            Self for chaining
        """
        self._query = self._query.limit(limit)
        return self

    def offset(self, offset: int) -> 'QueryBuilder[ModelType]':
        """
        Add offset

        Args:
            offset: Number of results to skip

        Returns:
            Self for chaining
        """
        self._query = self._query.offset(offset)
        return self

    def paginate(self, page: int = 1, size: int = 20) -> 'QueryBuilder[ModelType]':
        """
        Add pagination

        Args:
            page: Page number (1-indexed)
            size: Page size

        Returns:
            Self for chaining
        """
        self._page = page
        self._page_size = size
        skip = (page - 1) * size
        self._query = self._query.offset(skip).limit(size)
        return self

    def all(self) -> list[ModelType]:
        """
        Execute query and return all results

        Returns:
            List of model instances
        """
        return self._query.all()

    def first(self) -> ModelType | None:
        """
        Execute query and return first result

        Returns:
            First model instance or None
        """
        return self._query.first()

    def count(self) -> int:
        """
        Get count of results

        Returns:
            Number of matching records
        """
        return self._query.count()

    def paginated(self) -> tuple[list[ModelType], int]:
        """
        Execute paginated query and return results with total count

        Returns:
            Tuple of (items, total_count)
        """
        # Get total count before pagination
        count_query = self._query.with_entities(func.count(self.model.id))
        total = count_query.scalar()

        # Get paginated results
        items = self._query.all()

        return items, total

    def exists(self) -> bool:
        """
        Check if any records match the query

        Returns:
            True if records exist, False otherwise
        """
        return self._query.count() > 0
