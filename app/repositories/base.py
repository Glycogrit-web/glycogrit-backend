"""
Base repository with generic CRUD operations.

All entity-specific repositories should inherit from BaseRepository
to get standard database operations for free.
"""

from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.exceptions import DatabaseException

# Generic type for SQLAlchemy models
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository providing standard CRUD operations.

    Type Parameters:
        ModelType: The SQLAlchemy model class this repository manages
    """

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize the repository.

        Args:
            model: The SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def create(self, data: Dict[str, Any]) -> ModelType:
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

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Retrieve a record by its ID.

        Args:
            id: The record ID

        Returns:
            The model instance if found, None otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Retrieve all records with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def update(self, id: int, data: Dict[str, Any]) -> Optional[ModelType]:
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

    def find_by(self, **filters) -> List[ModelType]:
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

    def find_one_by(self, **filters) -> Optional[ModelType]:
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
