"""
CQRS Queries for Users Module

Queries represent read operations that don't change state.
Each query encapsulates a specific data retrieval operation.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GetUserByIdQuery:
    """Query to get user by ID"""
    user_id: int


@dataclass
class GetUserByEmailQuery:
    """Query to get user by email"""
    email: str


@dataclass
class GetUserByPhoneQuery:
    """Query to get user by phone"""
    phone: str


@dataclass
class GetUserByIdentifierQuery:
    """Query to get user by email or phone (auto-detect)"""
    identifier: str


@dataclass
class GetUserByOAuthQuery:
    """Query to get user by OAuth provider and ID"""
    oauth_provider: str
    oauth_id: str


@dataclass
class GetActiveUsersQuery:
    """Query to get all active users with pagination"""
    skip: int = 0
    limit: int = 100


@dataclass
class GetAllUsersQuery:
    """Query to get all users with pagination"""
    skip: int = 0
    limit: int = 100


@dataclass
class GetUsersByRoleQuery:
    """Query to get users by role"""
    role: str
    skip: int = 0
    limit: int = 100


@dataclass
class CountActiveUsersQuery:
    """Query to count active users"""
    pass


@dataclass
class CountUsersByRoleQuery:
    """Query to count users by role"""
    role: str
