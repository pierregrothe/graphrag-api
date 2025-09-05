# src/graphrag_api_service/database/models.py
# Database models for simplified SQLite architecture
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Database models for GraphRAG API Service - SQLite implementation."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import DeclarativeBase, relationship


def utc_now() -> datetime:
    """Helper function for SQLAlchemy default datetime values."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""

    pass


# Association table for many-to-many relationship between users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", PostgresUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", PostgresUUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)


class WorkspaceStatus(str, Enum):
    """Workspace status enum."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DELETED = "deleted"


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


class Role(Base):
    """Role model for RBAC."""

    __tablename__ = "roles"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")


class UserRole(Base):
    """UserRole association model (if needed for direct access)."""

    __tablename__ = "user_roles_direct"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id = Column(PostgresUUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)


class ApiKey(Base):
    """API Key model for authentication."""

    __tablename__ = "api_keys"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    permissions = Column(JSON, default=list)
    rate_limit = Column(Integer, default=1000)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")


class Workspace(Base):
    """Workspace model for multi-project support."""

    __tablename__ = "workspaces"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    owner_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status = Column(String(50), default="active")
    config = Column(JSON, default=dict)
    data_path = Column(String(500))
    workspace_path = Column(String(500))
    config_file_path = Column(String(500))
    workspace_metadata = Column(JSON, default=dict)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    indexing_jobs = relationship(
        "IndexingJob", back_populates="workspace", cascade="all, delete-orphan"
    )


class IndexingJob(Base):
    """Indexing job model for tracking GraphRAG indexing tasks."""

    __tablename__ = "indexing_jobs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id = Column(PostgresUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    status = Column(String(50), default="pending")
    progress = Column(Integer, default=0)
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    job_metadata = Column(JSON, default=dict)

    # Relationships
    workspace = relationship("Workspace", back_populates="indexing_jobs")


class AuditLog(Base):
    """Audit log model for tracking API usage."""

    __tablename__ = "audit_logs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")


# Pydantic models for API responses
class UserResponse(BaseModel):
    """User response model."""

    id: UUID
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    roles: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    """Role response model."""

    id: UUID
    name: str
    description: str | None
    permissions: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceResponse(BaseModel):
    """Workspace response model."""

    id: UUID
    name: str
    description: str | None
    status: str
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
