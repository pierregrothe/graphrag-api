"""
Administrative API key management for GraphRAG API Service.

This module provides comprehensive administrative capabilities for managing
API keys across all users with proper auditing and batch operations.
"""

import asyncio
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from .api_keys import APIKeyManager, APIKey, APIKeyRequest, APIKeyResponse, APIKeyScope
from .master_key import get_admin_audit_logger, AdminAuditLogger
from ..exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    ResourceNotFoundError,
    QuotaExceededError
)
from ..security import get_security_logger


class AdminAPIKeyRequest(BaseModel):
    """Administrative API key creation request."""
    
    name: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=255)
    scopes: List[APIKeyScope] = Field(default_factory=list)
    workspace_id: Optional[str] = None
    rate_limit_config: Optional[Dict[str, int]] = None
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650)
    description: Optional[str] = Field(None, max_length=500)
    created_by: str = Field(..., description="Admin user creating the key")


class AdminAPIKeyFilter(BaseModel):
    """Filter criteria for administrative API key queries."""
    
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    status: Optional[str] = None  # active, expired, revoked
    scopes: Optional[List[APIKeyScope]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    expires_after: Optional[datetime] = None
    expires_before: Optional[datetime] = None
    last_used_after: Optional[datetime] = None
    last_used_before: Optional[datetime] = None


class AdminAPIKeyUpdate(BaseModel):
    """Administrative API key update request."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    scopes: Optional[List[APIKeyScope]] = None
    rate_limit_config: Optional[Dict[str, int]] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)
    updated_by: str = Field(..., description="Admin user updating the key")


class BatchOperation(BaseModel):
    """Batch operation request."""
    
    operation: str = Field(..., description="Operation type: revoke, update, rotate")
    filters: AdminAPIKeyFilter
    updates: Optional[AdminAPIKeyUpdate] = None
    reason: Optional[str] = Field(None, max_length=500)
    performed_by: str = Field(..., description="Admin user performing batch operation")


class BatchOperationResult(BaseModel):
    """Batch operation result."""
    
    operation_id: str
    operation: str
    total_keys: int
    successful_operations: int
    failed_operations: int
    errors: List[Dict[str, str]]
    affected_key_ids: List[str]
    timestamp: datetime


class AdminAPIKeyManager(APIKeyManager):
    """Administrative API key manager with enhanced capabilities."""
    
    def __init__(self):
        super().__init__()
        self.security_logger = get_security_logger()
        self.audit_logger = get_admin_audit_logger()
    
    async def list_all_keys(
        self,
        filters: Optional[AdminAPIKeyFilter] = None,
        limit: int = 100,
        offset: int = 0,
        admin_user_id: str = "master_admin"
    ) -> Tuple[List[APIKey], int]:
        """List all API keys with administrative filtering.
        
        Args:
            filters: Filter criteria
            limit: Maximum number of keys to return
            offset: Number of keys to skip
            admin_user_id: ID of admin performing the operation
            
        Returns:
            Tuple of (filtered keys, total count)
        """
        # Get all keys
        all_keys = list(self.api_keys.values())
        
        # Apply filters
        if filters:
            all_keys = self._apply_filters(all_keys, filters)
        
        # Sort by creation date (newest first)
        all_keys.sort(key=lambda k: k.created_at, reverse=True)
        
        # Apply pagination
        total_count = len(all_keys)
        paginated_keys = all_keys[offset:offset + limit]
        
        # Log admin operation
        self.audit_logger.log_admin_operation(
            operation_id=str(uuid4()),
            admin_user_id=admin_user_id,
            operation_type="list_all_keys",
            affected_resources=[],
            success=True
        )
        
        return paginated_keys, total_count
    
    async def create_admin_key(
        self,
        request: AdminAPIKeyRequest,
        admin_user_id: str = "master_admin"
    ) -> APIKeyResponse:
        """Create API key for any user with administrative privileges.
        
        Args:
            request: API key creation request
            admin_user_id: ID of admin creating the key
            
        Returns:
            Created API key response
        """
        operation_id = str(uuid4())
        
        try:
            # Convert to regular API key request
            api_key_request = APIKeyRequest(
                name=request.name,
                scopes=request.scopes,
                workspace_id=request.workspace_id,
                expires_in_days=request.expires_in_days,
                description=request.description
            )
            
            # Create the key
            response = await self.create_api_key(
                user_id=request.user_id,
                request=api_key_request
            )
            
            # Log successful creation
            self.audit_logger.log_admin_operation(
                operation_id=operation_id,
                admin_user_id=admin_user_id,
                operation_type="create_user_key",
                affected_resources=[response.id],
                success=True,
                after_state={
                    "key_id": response.id,
                    "user_id": request.user_id,
                    "scopes": [scope.value for scope in request.scopes]
                }
            )
            
            return response
            
        except Exception as e:
            # Log failed creation
            self.audit_logger.log_admin_operation(
                operation_id=operation_id,
                admin_user_id=admin_user_id,
                operation_type="create_user_key",
                affected_resources=[],
                success=False,
                error_message=str(e)
            )
            raise
    
    async def get_key_details(
        self,
        key_id: str,
        admin_user_id: str = "master_admin"
    ) -> Optional[APIKey]:
        """Get detailed API key information.
        
        Args:
            key_id: API key ID
            admin_user_id: ID of admin requesting details
            
        Returns:
            API key details or None if not found
        """
        key = self.api_keys.get(key_id)
        
        if key:
            # Log admin access
            self.audit_logger.log_admin_operation(
                operation_id=str(uuid4()),
                admin_user_id=admin_user_id,
                operation_type="view_key_details",
                affected_resources=[key_id],
                success=True
            )
        
        return key
    
    async def update_key_admin(
        self,
        key_id: str,
        updates: AdminAPIKeyUpdate,
        admin_user_id: str = "master_admin"
    ) -> bool:
        """Update API key with administrative privileges.
        
        Args:
            key_id: API key ID to update
            updates: Update data
            admin_user_id: ID of admin performing update
            
        Returns:
            True if update successful
        """
        operation_id = str(uuid4())
        
        try:
            key = self.api_keys.get(key_id)
            if not key:
                raise ResourceNotFoundError(
                    f"API key {key_id} not found",
                    resource_type="api_key",
                    resource_id=key_id
                )
            
            # Store before state
            before_state = key.dict()
            
            # Apply updates
            if updates.name is not None:
                key.name = updates.name
            if updates.scopes is not None:
                key.scopes = updates.scopes
            if updates.rate_limit_config is not None:
                # Update rate limit config
                for field, value in updates.rate_limit_config.items():
                    if hasattr(key.rate_limit_config, field):
                        setattr(key.rate_limit_config, field, value)
            if updates.expires_at is not None:
                key.expires_at = updates.expires_at
            if updates.is_active is not None:
                key.is_active = updates.is_active
            
            # Log successful update
            self.audit_logger.log_admin_operation(
                operation_id=operation_id,
                admin_user_id=admin_user_id,
                operation_type="update_key",
                affected_resources=[key_id],
                success=True,
                before_state=before_state,
                after_state=key.dict()
            )
            
            return True
            
        except Exception as e:
            # Log failed update
            self.audit_logger.log_admin_operation(
                operation_id=operation_id,
                admin_user_id=admin_user_id,
                operation_type="update_key",
                affected_resources=[key_id],
                success=False,
                error_message=str(e)
            )
            raise
    
    async def revoke_key_admin(
        self,
        key_id: str,
        reason: Optional[str] = None,
        admin_user_id: str = "master_admin"
    ) -> bool:
        """Revoke API key with administrative privileges.
        
        Args:
            key_id: API key ID to revoke
            reason: Reason for revocation
            admin_user_id: ID of admin performing revocation
            
        Returns:
            True if revocation successful
        """
        operation_id = str(uuid4())
        
        try:
            key = self.api_keys.get(key_id)
            if not key:
                raise ResourceNotFoundError(
                    f"API key {key_id} not found",
                    resource_type="api_key",
                    resource_id=key_id
                )
            
            # Store before state
            before_state = key.dict()
            
            # Revoke key
            key.is_active = False
            
            # Log successful revocation
            self.audit_logger.log_admin_operation(
                operation_id=operation_id,
                admin_user_id=admin_user_id,
                operation_type="revoke_key",
                affected_resources=[key_id],
                success=True,
                before_state=before_state,
                after_state=key.dict()
            )
            
            return True
            
        except Exception as e:
            # Log failed revocation
            self.audit_logger.log_admin_operation(
                operation_id=operation_id,
                admin_user_id=admin_user_id,
                operation_type="revoke_key",
                affected_resources=[key_id],
                success=False,
                error_message=str(e)
            )
            raise
    
    def _apply_filters(self, keys: List[APIKey], filters: AdminAPIKeyFilter) -> List[APIKey]:
        """Apply filters to key list."""
        filtered_keys = keys
        
        if filters.user_id:
            filtered_keys = [k for k in filtered_keys if k.user_id == filters.user_id]
        
        if filters.workspace_id:
            filtered_keys = [k for k in filtered_keys if k.workspace_id == filters.workspace_id]
        
        if filters.status:
            now = datetime.now(UTC)
            if filters.status == "active":
                filtered_keys = [k for k in filtered_keys if k.is_active and (not k.expires_at or k.expires_at > now)]
            elif filters.status == "expired":
                filtered_keys = [k for k in filtered_keys if k.expires_at and k.expires_at <= now]
            elif filters.status == "revoked":
                filtered_keys = [k for k in filtered_keys if not k.is_active]
        
        if filters.scopes:
            filtered_keys = [k for k in filtered_keys if any(scope in k.scopes for scope in filters.scopes)]
        
        if filters.created_after:
            filtered_keys = [k for k in filtered_keys if k.created_at >= filters.created_after]
        
        if filters.created_before:
            filtered_keys = [k for k in filtered_keys if k.created_at <= filters.created_before]
        
        if filters.expires_after and filters.expires_after:
            filtered_keys = [k for k in filtered_keys if k.expires_at and k.expires_at >= filters.expires_after]
        
        if filters.expires_before:
            filtered_keys = [k for k in filtered_keys if k.expires_at and k.expires_at <= filters.expires_before]
        
        if filters.last_used_after:
            filtered_keys = [k for k in filtered_keys if k.last_used_at and k.last_used_at >= filters.last_used_after]
        
        if filters.last_used_before:
            filtered_keys = [k for k in filtered_keys if k.last_used_at and k.last_used_at <= filters.last_used_before]
        
        return filtered_keys

    async def batch_operation(
        self,
        batch_request: BatchOperation,
        admin_user_id: str = "master_admin"
    ) -> BatchOperationResult:
        """Perform batch operations on API keys.

        Args:
            batch_request: Batch operation request
            admin_user_id: ID of admin performing batch operation

        Returns:
            Batch operation result
        """
        operation_id = str(uuid4())

        try:
            # Get keys matching filters
            all_keys = list(self.api_keys.values())
            filtered_keys = self._apply_filters(all_keys, batch_request.filters)

            successful_operations = 0
            failed_operations = 0
            errors = []
            affected_key_ids = []

            # Perform operation on each key
            for key in filtered_keys:
                try:
                    if batch_request.operation == "revoke":
                        await self.revoke_key_admin(
                            key.id,
                            reason=batch_request.reason,
                            admin_user_id=admin_user_id
                        )
                        successful_operations += 1
                        affected_key_ids.append(key.id)

                    elif batch_request.operation == "update" and batch_request.updates:
                        await self.update_key_admin(
                            key.id,
                            batch_request.updates,
                            admin_user_id=admin_user_id
                        )
                        successful_operations += 1
                        affected_key_ids.append(key.id)

                    elif batch_request.operation == "rotate":
                        # Rotate key (generate new key value)
                        await self.rotate_key(key.id, key.user_id)
                        successful_operations += 1
                        affected_key_ids.append(key.id)

                    else:
                        raise ValidationError(f"Unknown batch operation: {batch_request.operation}")

                except Exception as e:
                    failed_operations += 1
                    errors.append({
                        "key_id": key.id,
                        "error": str(e)
                    })

            result = BatchOperationResult(
                operation_id=operation_id,
                operation=batch_request.operation,
                total_keys=len(filtered_keys),
                successful_operations=successful_operations,
                failed_operations=failed_operations,
                errors=errors,
                affected_key_ids=affected_key_ids,
                timestamp=datetime.now(UTC)
            )

            # Log batch operation
            self.audit_logger.log_admin_operation(
                operation_id=operation_id,
                admin_user_id=admin_user_id,
                operation_type="batch_operation",
                affected_resources=affected_key_ids,
                success=failed_operations == 0,
                after_state={
                    "operation": batch_request.operation,
                    "total_keys": len(filtered_keys),
                    "successful": successful_operations,
                    "failed": failed_operations
                }
            )

            return result

        except Exception as e:
            # Log failed batch operation
            self.audit_logger.log_admin_operation(
                operation_id=operation_id,
                admin_user_id=admin_user_id,
                operation_type="batch_operation",
                affected_resources=[],
                success=False,
                error_message=str(e)
            )
            raise


# Global admin API key manager
_admin_api_key_manager = AdminAPIKeyManager()


def get_admin_api_key_manager() -> AdminAPIKeyManager:
    """Get the global admin API key manager instance."""
    return _admin_api_key_manager
