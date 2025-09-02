# src/graphrag_api_service/database/models.py
# Database models for GraphRAG API service
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""SQLAlchemy database models for users, workspaces, and jobs."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base

# Association table for user roles (many-to-many)
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile information
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Multi-tenancy support
    tenant_id = Column(String(255), index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_login_at = Column(DateTime(timezone=True))

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Role(Base):
    """Role model for role-based access control."""

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    permissions = Column(JSON, default=list, nullable=False)  # List of permission strings

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class APIKey(Base):
    """API key model for API authentication."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    prefix = Column(String(20), nullable=False, index=True)

    # Ownership and permissions
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String(255), index=True)
    permissions = Column(JSON, default=list, nullable=False)  # List of permission strings

    # Configuration
    rate_limit = Column(Integer, default=1000, nullable=False)  # requests per hour
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class Workspace(Base):
    """Workspace model for GraphRAG workspaces."""

    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String(255), index=True)

    # Configuration
    config = Column(JSON, nullable=False)  # Workspace configuration as JSON

    # Paths
    data_path = Column(String(1000), nullable=False)
    workspace_path = Column(String(1000))
    config_file_path = Column(String(1000))

    # Status
    status = Column(String(50), default="created", nullable=False, index=True)
    last_error = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_accessed_at = Column(DateTime(timezone=True))

    # Relationships
    owner = relationship("User", back_populates="workspaces")
    indexing_jobs = relationship(
        "IndexingJob", back_populates="workspace", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"


class IndexingJob(Base):
    """Indexing job model for GraphRAG indexing operations."""

    __tablename__ = "indexing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Job configuration
    config = Column(JSON, nullable=False)  # Job configuration as JSON

    # Status and progress
    status = Column(String(50), default="pending", nullable=False, index=True)
    stage = Column(String(100))
    progress_percentage = Column(Integer, default=0, nullable=False)

    # Results and metrics
    result = Column(JSON)  # Job results as JSON
    error_message = Column(Text)

    # Statistics
    files_processed = Column(Integer, default=0, nullable=False)
    entities_extracted = Column(Integer, default=0, nullable=False)
    relationships_extracted = Column(Integer, default=0, nullable=False)

    # Retry logic
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="indexing_jobs")

    def __repr__(self):
        return (
            f"<IndexingJob(id={self.id}, workspace_id={self.workspace_id}, status='{self.status}')>"
        )
