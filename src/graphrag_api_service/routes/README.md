# 🛣️ REST API Routes Module

The routes module provides comprehensive REST API endpoints with OpenAPI documentation, security middleware, and 100% feature parity with the GraphQL API.

## 📁 Module Structure

```
routes/
├── __init__.py              # Module exports
├── auth.py                 # Authentication endpoints
├── graph.py                # Graph operations endpoints
├── health.py               # Health check endpoints
├── indexing.py             # Indexing job endpoints
├── system.py               # System management endpoints
├── workspaces.py           # Workspace management endpoints
└── README.md               # This documentation
```

## 🔧 Core Endpoints

### Graph Operations (`graph.py`)

**Security Enhancement**: All endpoints now include comprehensive path traversal protection.

```python
# GET /api/graph/entities - Query graph entities
@router.get("/entities")
async def get_entities(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    entity_name: str | None = Query(None),
    entity_type: str | None = Query(None),
    workspace_id: str = Query("default"),
    graph_operations: GraphOperationsDep = None,
) -> dict[str, Any]:
    """Get entities with secure path validation."""
    settings = get_settings()
    data_path = validate_workspace_path(workspace_id, settings)  # Security protection

    entities = await graph_operations.get_entities(
        data_path=data_path,
        limit=limit,
        offset=offset,
        entity_name=entity_name,
        entity_type=entity_type
    )

    return {
        "entities": entities,
        "total_count": len(entities),
        "limit": limit,
        "offset": offset,
        "workspace_id": workspace_id
    }

# GET /api/graph/relationships - Query relationships
@router.get("/relationships")
async def get_relationships(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    source_entity: str | None = Query(None),
    target_entity: str | None = Query(None),
    relationship_type: str | None = Query(None),
    workspace_id: str = Query("default"),
    graph_operations: GraphOperationsDep = None,
) -> dict[str, Any]:
    """Get relationships with filtering."""
    settings = get_settings()
    data_path = validate_workspace_path(workspace_id, settings)

    relationships = await graph_operations.get_relationships(
        data_path=data_path,
        limit=limit,
        offset=offset,
        source_entity=source_entity,
        target_entity=target_entity,
        relationship_type=relationship_type
    )

    return {
        "relationships": relationships,
        "total_count": len(relationships),
        "limit": limit,
        "offset": offset
    }
```

### Workspace Management (`workspaces.py`)

```python
# POST /api/workspaces - Create workspace
@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    workspace: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new workspace with validation."""
    return await workspace_service.create_workspace(
        name=workspace.name,
        description=workspace.description,
        config=workspace.config,
        owner_id=current_user.id,
        db=db
    )

# GET /api/workspaces - List workspaces
@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's workspaces."""
    return await workspace_service.get_user_workspaces(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=status,
        db=db
    )

# PUT /api/workspaces/{workspace_id} - Update workspace
@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    updates: WorkspaceUpdate,
    current_user: User = Depends(require_workspace_access("write")),
    db: Session = Depends(get_db)
):
    """Update workspace with permission check."""
    return await workspace_service.update_workspace(
        workspace_id=workspace_id,
        updates=updates.dict(exclude_unset=True),
        db=db
    )
```

### Authentication (`auth.py`)

```python
# POST /api/auth/login - User login
@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    user = await auth_service.authenticate_user(
        email=credentials.email,
        password=credentials.password,
        db=db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token = jwt_manager.create_access_token(
        data={"sub": user.email, "roles": user.roles}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800
    }

# POST /api/auth/register - User registration
@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user account."""
    return await auth_service.create_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        db=db
    )
```

### System Management (`system.py`)

```python
# GET /api/system/status - System status
@router.get("/status")
async def get_system_status(
    current_user: User = Depends(require_permission("read:system"))
):
    """Get comprehensive system status."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime": get_uptime(),
        "database": await check_database_health(),
        "cache": await check_cache_health(),
        "services": await check_service_health()
    }

# GET /api/system/metrics - System metrics
@router.get("/metrics")
async def get_system_metrics(
    current_user: User = Depends(require_permission("read:metrics"))
):
    """Get system performance metrics."""
    return await monitoring_service.get_current_metrics()
```

## 🔐 Security Features

### Path Traversal Protection

All graph endpoints now include comprehensive security validation:

```python
def validate_workspace_path(workspace_id: str | None, settings) -> str:
    """Validate and resolve workspace path to prevent traversal attacks.

    Parameters
    ----------
    workspace_id : str | None
        User-provided workspace identifier
    settings : object
        Application settings containing base paths

    Returns
    -------
    str
        Validated and resolved data path

    Raises
    ------
    HTTPException
        If path validation fails
    """
    # Use default path if no workspace_id provided
    if not workspace_id or workspace_id == "default":
        data_path = settings.graphrag_data_path
        if not data_path:
            raise HTTPException(status_code=400, detail="No default data path configured")
        return data_path

    # Validate workspace_id format (prevent obvious attacks)
    if not workspace_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid workspace ID format")

    # Construct safe workspace path
    base_workspaces_path = getattr(settings, 'base_workspaces_path', 'workspaces')

    try:
        # Resolve paths to absolute paths
        base_path = Path(base_workspaces_path).resolve()
        workspace_path = (base_path / workspace_id).resolve()

        # Ensure the resolved path is within the base directory
        if not str(workspace_path).startswith(str(base_path)):
            raise HTTPException(status_code=403, detail="Access to workspace denied")

        # Check if workspace directory exists
        if not workspace_path.exists():
            raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")

        return str(workspace_path)

    except (OSError, ValueError) as e:
        logger.error(f"Path validation error for workspace '{workspace_id}': {e}")
        raise HTTPException(status_code=400, detail="Invalid workspace path") from e
```

### Authentication Middleware

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)) -> User:
    """Extract and validate current user from JWT token."""
    try:
        payload = jwt_manager.verify_token(token.credentials)
        user = await user_service.get_user_by_email(payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user"
            )
        return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

def require_permission(permission: str):
    """Require specific permission for endpoint access."""
    async def permission_checker(current_user: User = Depends(get_current_user)):
        if not rbac.has_permission(current_user.roles, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return permission_checker
```

## 📊 API Documentation

### OpenAPI Schema

All endpoints include comprehensive OpenAPI documentation:

```python
@router.get(
    "/entities",
    summary="Get Graph Entities",
    description="Retrieve entities from the knowledge graph with filtering and pagination",
    response_description="List of entities with metadata",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "entities": [
                            {
                                "id": "entity_123",
                                "name": "Microsoft",
                                "type": "Organization",
                                "description": "Technology company",
                                "degree": 25
                            }
                        ],
                        "total_count": 1,
                        "limit": 50,
                        "offset": 0
                    }
                }
            }
        },
        400: {"description": "Invalid parameters"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Workspace not found"}
    },
    tags=["Graph Operations"]
)
```

### Request/Response Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    description: Optional[str] = None
    degree: int
    community_id: Optional[str] = None
    created_at: datetime

class EntitiesResponse(BaseModel):
    entities: List[EntityResponse]
    total_count: int
    limit: int
    offset: int
    workspace_id: str

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    config: Optional[dict] = None

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    config: dict
    status: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

## 🧪 Testing

### Endpoint Testing

```python
import pytest
from fastapi.testclient import TestClient
from graphrag_api_service.main import app

client = TestClient(app)

def test_get_entities_unauthorized():
    response = client.get("/api/graph/entities")
    assert response.status_code == 401

def test_get_entities_with_auth(auth_headers):
    response = client.get(
        "/api/graph/entities?limit=10&workspace_id=test-workspace",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "entities" in data
    assert len(data["entities"]) <= 10

def test_path_traversal_protection(auth_headers):
    # Attempt path traversal attack
    response = client.get(
        "/api/graph/entities?workspace_id=../../../etc/passwd",
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "Invalid workspace ID format" in response.json()["detail"]

def test_create_workspace(auth_headers):
    workspace_data = {
        "name": "Test Workspace",
        "description": "Test description"
    }
    response = client.post(
        "/api/workspaces",
        json=workspace_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Workspace"
```

## 📈 Performance Features

### Response Caching

```python
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

@router.get("/statistics")
@cache(expire=300)  # Cache for 5 minutes
async def get_graph_statistics(
    workspace_id: str = Query("default"),
    current_user: User = Depends(get_current_user)
):
    """Get cached graph statistics."""
    settings = get_settings()
    data_path = validate_workspace_path(workspace_id, settings)

    return await graph_operations.get_statistics(data_path)
```

### Request Validation

```python
from fastapi import Query
from typing import Annotated

# Type-safe query parameters
LimitQuery = Annotated[int, Query(ge=1, le=1000, description="Number of items to return")]
OffsetQuery = Annotated[int, Query(ge=0, description="Number of items to skip")]
WorkspaceQuery = Annotated[str, Query(description="Workspace identifier")]

@router.get("/entities")
async def get_entities(
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    workspace_id: WorkspaceQuery = "default"
):
    """Type-safe endpoint with validation."""
    pass
```

## 🚨 Best Practices

1. **Security First**: Always validate and sanitize inputs
2. **Path Protection**: Use secure path validation for all file operations
3. **Authentication**: Require authentication for all sensitive endpoints
4. **Authorization**: Implement granular permission checks
5. **Input Validation**: Use Pydantic models for request validation
6. **Error Handling**: Provide meaningful error messages
7. **Documentation**: Maintain comprehensive OpenAPI documentation
8. **Testing**: Write comprehensive endpoint tests
9. **Caching**: Cache expensive operations appropriately
10. **Monitoring**: Track endpoint performance and usage

## 🔧 Configuration

### Route Configuration

```python
# Configure route prefixes and tags
ROUTE_CONFIG = {
    "auth": {"prefix": "/api/auth", "tags": ["Authentication"]},
    "workspaces": {"prefix": "/api/workspaces", "tags": ["Workspaces"]},
    "graph": {"prefix": "/api/graph", "tags": ["Graph Operations"]},
    "indexing": {"prefix": "/api/indexing", "tags": ["Indexing"]},
    "system": {"prefix": "/api/system", "tags": ["System Management"]}
}

# Apply configuration
for module_name, config in ROUTE_CONFIG.items():
    router = getattr(routes, f"{module_name}_router")
    app.include_router(router, **config)
```

### Security Configuration

```bash
# API Security Settings
API_RATE_LIMIT_REQUESTS=100
API_RATE_LIMIT_WINDOW=60
API_MAX_REQUEST_SIZE=10MB
API_CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]

# Path Security
BASE_WORKSPACES_PATH=workspaces
ALLOW_WORKSPACE_CREATION=true
MAX_WORKSPACE_SIZE_GB=10
```

---

For more information, see the [main documentation](../../../README.md) or other module documentation.
