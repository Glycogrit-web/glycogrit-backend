"""
Base Repository Pattern
Provides generic CRUD operations for all models
Follows the Repository Pattern for data access abstraction
"""
from typing import Generic, TypeVar, Type, List, Optional, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base Repository implementing generic CRUD operations

    This follows the Repository Pattern to:
    1. Abstract database access logic
    2. Provide consistent interface across all models
    3. Make testing easier with mock repositories
    4. Centralize query logic and optimizations

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: Session):
                super().__init__(User, db)

            def find_by_email(self, email: str) -> Optional[User]:
                return self.db.query(self.model).filter(
                    self.model.email == email
                ).first()
    """

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def get(self, id: Any) -> Optional[ModelType]:
        """
        Get a single record by ID

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        **filters
    ) -> List[ModelType]:
        """
        Get all records with optional pagination and filtering

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            order_by: Column name to order by (prefix with - for descending)
            **filters: Keyword arguments for filtering (column=value)

        Returns:
            List of model instances
        """
        query = self.db.query(self.model)

        # Apply filters
        if filters:
            filter_conditions = [
                getattr(self.model, key) == value
                for key, value in filters.items()
                if hasattr(self.model, key)
            ]
            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
                # Descending order
                column_name = order_by[1:]
                if hasattr(self.model, column_name):
                    query = query.order_by(getattr(self.model, column_name).desc())
            else:
                # Ascending order
                if hasattr(self.model, order_by):
                    query = query.order_by(getattr(self.model, order_by))

        return query.offset(skip).limit(limit).all()

    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record

        Args:
            obj_in: Dictionary of model attributes

        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, id: Any, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update an existing record

        Args:
            id: Primary key value
            obj_in: Dictionary of attributes to update

        Returns:
            Updated model instance or None if not found
        """
        db_obj = self.get(id)
        if not db_obj:
            return None

        for key, value in obj_in.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: Any) -> bool:
        """
        Delete a record

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found
        """
        db_obj = self.get(id)
        if not db_obj:
            return False

        self.db.delete(db_obj)
        self.db.commit()
        return True

    def count(self, **filters) -> int:
        """
        Count records with optional filtering

        Args:
            **filters: Keyword arguments for filtering

        Returns:
            Number of matching records
        """
        query = self.db.query(self.model)

        if filters:
            filter_conditions = [
                getattr(self.model, key) == value
                for key, value in filters.items()
                if hasattr(self.model, key)
            ]
            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

        return query.count()

    def exists(self, **filters) -> bool:
        """
        Check if any records exist matching the filters

        Args:
            **filters: Keyword arguments for filtering

        Returns:
            True if at least one record exists
        """
        return self.count(**filters) > 0

    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records efficiently

        Args:
            objects: List of dictionaries containing model attributes

        Returns:
            List of created model instances
        """
        db_objects = [self.model(**obj) for obj in objects]
        self.db.bulk_save_objects(db_objects, return_defaults=True)
        self.db.commit()
        return db_objects

    def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records efficiently

        Args:
            updates: List of dictionaries with 'id' and fields to update

        Returns:
            Number of records updated
        """
        count = 0
        for update_data in updates:
            if 'id' not in update_data:
                continue

            id_value = update_data.pop('id')
            result = self.db.query(self.model).filter(
                self.model.id == id_value
            ).update(update_data)
            count += result

        self.db.commit()
        return count
