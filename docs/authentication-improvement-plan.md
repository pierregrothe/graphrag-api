# Authentication & Security Improvement Plan

## Executive Summary

Enhance the GraphRAG API Service authentication to provide both simple (API keys) and advanced (JWT) authentication options, with clear documentation and ready-to-use examples.

## Phase 1: Complete JWT Implementation (Week 1)

### 1.1 Wire Authentication to Endpoints
**Priority**: High  
**Effort**: 8 hours

- Add authentication dependencies to all protected routes
- Implement proper user database storage
- Create authentication middleware that actually validates tokens
- Add role-based permissions to each endpoint

**Tasks**:
- Create `auth_deps.py` with reusable authentication dependencies
- Add `@Depends(verify_token)` to protected endpoints
- Implement user CRUD operations in database
- Add permission decorators for role-based access

### 1.2 Create Authentication Endpoints
**Priority**: High  
**Effort**: 4 hours

- `/api/auth/register` - User registration
- `/api/auth/login` - Get access/refresh tokens
- `/api/auth/refresh` - Refresh access token
- `/api/auth/logout` - Token revocation
- `/api/auth/profile` - Get current user info

### 1.3 Implement Token Storage
**Priority**: Medium  
**Effort**: 4 hours

- Add token blacklist for logout
- Store refresh tokens securely
- Implement token rotation on refresh
- Add session management

## Phase 2: Add API Key Authentication (Week 1-2)

### 2.1 Design API Key System
**Priority**: High  
**Effort**: 6 hours

Simple API key authentication for easier integration:

```python
# Headers approach
Authorization: Bearer <api_key>
X-API-Key: <api_key>

# Query parameter (for webhooks/simple integrations)
?api_key=<api_key>
```

**Features**:
- Generate API keys per user/workspace
- Set expiration dates
- Scope/permission limitations
- Rate limiting per key
- Key rotation support

### 2.2 Implement API Key Management
**Priority**: High  
**Effort**: 8 hours

**Database Schema**:
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE,
    user_id UUID REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    name VARCHAR(100),
    permissions JSON,
    rate_limit INTEGER,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP,
    is_active BOOLEAN
);
```

**API Endpoints**:
- `POST /api/auth/keys` - Generate new API key
- `GET /api/auth/keys` - List user's API keys
- `DELETE /api/auth/keys/{key_id}` - Revoke API key
- `PUT /api/auth/keys/{key_id}/rotate` - Rotate key

### 2.3 Dual Authentication Support
**Priority**: Medium  
**Effort**: 4 hours

Allow both JWT and API key authentication:

```python
async def get_current_user(
    authorization: str = Header(None),
    x_api_key: str = Header(None),
    api_key: str = Query(None)
):
    # Check API key first (simpler)
    if x_api_key or api_key:
        return await verify_api_key(x_api_key or api_key)
    
    # Fall back to JWT
    if authorization:
        return await verify_jwt_token(authorization)
    
    raise HTTPException(401, "Authentication required")
```

## Phase 3: Simplify Microsoft GraphRAG Integration (Week 2)

### 3.1 Create GraphRAG Auth Wrapper
**Priority**: High  
**Effort**: 6 hours

Simplify GraphRAG's complex authentication:

```python
class GraphRAGAuthenticator:
    """
    Handles all GraphRAG authentication complexities
    """
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        
    def get_llm_config(self):
        """Auto-configure based on provider"""
        if self.provider == "ollama":
            return self._ollama_config()
        elif self.provider == "google_gemini":
            return self._gemini_config()
        elif self.provider == "azure_openai":
            return self._azure_config()
            
    def _validate_credentials(self):
        """Check all required credentials are present"""
        pass
```

### 3.2 Provider-Specific Authentication Guides
**Priority**: High  
**Effort**: 4 hours per provider

Create clear guides for each provider:

1. **Ollama (Local)**
   - No authentication needed
   - Just URL configuration
   
2. **Google Gemini**
   - API key acquisition guide
   - Vertex AI setup (advanced)
   - Service account configuration
   
3. **Azure OpenAI**
   - API key vs Azure AD
   - Endpoint configuration
   - Model deployment names

4. **OpenAI**
   - API key management
   - Organization ID setup

## Phase 4: Enhanced Documentation (Week 2-3)

### 4.1 Authentication Quick Start Guide
**Priority**: Critical  
**Effort**: 8 hours

Create comprehensive documentation:

```markdown
# Authentication Quick Start

## Option 1: Simple API Key (Recommended for most users)

### Step 1: Get your API key
POST http://localhost:8001/api/auth/register
{
    "username": "your-username",
    "password": "your-password",
    "email": "your@email.com"
}

Response:
{
    "api_key": "grag_ak_1234567890abcdef",
    "user_id": "...",
    "expires_at": "2025-12-31"
}

### Step 2: Use the API key
GET http://localhost:8001/api/workspaces
Headers:
  X-API-Key: grag_ak_1234567890abcdef

## Option 2: JWT Tokens (Advanced)
...
```

### 4.2 Interactive API Documentation
**Priority**: High  
**Effort**: 6 hours

- Add authentication UI to Swagger/ReDoc
- Provide "Try it out" functionality
- Include example requests for each auth method
- Add copy-paste curl commands

### 4.3 Postman Collection
**Priority**: Medium  
**Effort**: 4 hours

Create ready-to-use Postman collection:

```json
{
  "name": "GraphRAG API",
  "auth": {
    "type": "apikey",
    "apikey": {
      "key": "X-API-Key",
      "value": "{{api_key}}"
    }
  },
  "variables": [
    {
      "key": "base_url",
      "value": "http://localhost:8001"
    },
    {
      "key": "api_key",
      "value": "your_api_key_here"
    }
  ],
  "requests": [...]
}
```

### 4.4 SDK/Client Libraries
**Priority**: Low  
**Effort**: 8 hours per language

Python client example:

```python
from graphrag_client import GraphRAGClient

# Simple API key auth
client = GraphRAGClient(
    api_key="grag_ak_1234567890abcdef",
    base_url="http://localhost:8001"
)

# Create workspace
workspace = client.workspaces.create(
    name="my-workspace",
    chunk_size=1500
)

# Query
results = client.query(
    workspace_id=workspace.id,
    query="What is GraphRAG?",
    mode="global"
)
```

## Phase 5: Security Enhancements (Week 3)

### 5.1 Rate Limiting per Auth Method
**Priority**: Medium  
**Effort**: 4 hours

- Different limits for API keys vs JWT
- Per-endpoint rate limits
- Workspace-based quotas

### 5.2 Audit Logging
**Priority**: Medium  
**Effort**: 6 hours

Track all authentication events:
- Login attempts
- API key usage
- Permission denials
- Token refreshes

### 5.3 Security Headers & CORS
**Priority**: High  
**Effort**: 2 hours

- Proper CORS configuration
- Security headers (HSTS, CSP, etc.)
- Request signing for webhooks

## Implementation Priority

### Week 1: Core Authentication
1. Complete JWT implementation
2. Add authentication endpoints
3. Start API key design

### Week 2: API Keys & Integration
1. Implement API key system
2. GraphRAG auth wrapper
3. Provider guides

### Week 3: Documentation & Polish
1. Quick start guide
2. Interactive docs
3. Security enhancements

## Success Metrics

- **Adoption**: 80% of users choose API keys over JWT
- **Documentation**: <5 minutes to first authenticated request
- **Security**: Zero authentication bypasses in testing
- **Performance**: <10ms auth overhead per request

## Code Examples

### Simple API Key Middleware

```python
# src/graphrag_api_service/auth/api_keys.py

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

async def verify_api_key(
    api_key_header: str = Security(api_key_header),
    api_key_query: str = Security(api_key_query)
):
    api_key = api_key_header or api_key_query
    
    if not api_key:
        raise HTTPException(401, "API key required")
    
    # Verify key in database
    key_data = await db.get_api_key(api_key)
    if not key_data or not key_data.is_active:
        raise HTTPException(401, "Invalid API key")
    
    # Update last used
    await db.update_last_used(api_key)
    
    return key_data.user
```

### Using in Routes

```python
# src/graphrag_api_service/routes/workspace.py

from ..auth.api_keys import verify_api_key

@router.get("/workspaces")
async def list_workspaces(
    user=Depends(verify_api_key),  # Simple!
    workspace_manager: WorkspaceManagerDep = None
):
    # User is authenticated
    return await workspace_manager.list_workspaces(user_id=user.id)
```

### Environment Configuration

The authentication system can be fully configured via `.env` file for different deployment scenarios:

#### Quick Start (Development)

```env
# Minimal configuration for local development
AUTH_MODE=api_key
AUTH_ENABLED=true
DEFAULT_ADMIN_API_KEY=grag_ak_default_admin_change_this_immediately
AUTO_CREATE_ADMIN=true
```

With this configuration, you can immediately use the API:
```bash
curl -H "X-API-Key: grag_ak_default_admin_change_this_immediately" \
     http://localhost:8001/api/workspaces
```

#### Full Configuration Options

```env
# =============================================================================
# AUTHENTICATION & SECURITY
# =============================================================================
# Authentication mode: "none", "api_key", "jwt", "both"
# - none: No authentication (development only!)
# - api_key: Simple API key authentication (recommended)
# - jwt: JWT token-based authentication (advanced)
# - both: Support both API keys and JWT tokens
AUTH_MODE=api_key

# Enable/disable authentication globally
AUTH_ENABLED=true

# -----------------------------------------------------------------------------
# DEFAULT ADMIN ACCESS (Quick Start)
# -----------------------------------------------------------------------------
# Default admin API key for immediate access (CHANGE IN PRODUCTION!)
# This key has full admin privileges - use for initial setup only
DEFAULT_ADMIN_API_KEY=grag_ak_default_admin_change_this_immediately

# Default admin user (created on first startup if not exists)
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_EMAIL=admin@localhost
DEFAULT_ADMIN_PASSWORD=admin123  # Only used if JWT mode is enabled

# Auto-create default admin on startup
AUTO_CREATE_ADMIN=true

# -----------------------------------------------------------------------------
# API KEY CONFIGURATION
# -----------------------------------------------------------------------------
# API key prefix (helps identify keys in logs)
API_KEY_PREFIX=grag_ak_

# API key length (excluding prefix)
API_KEY_LENGTH=32

# Default API key expiration (days, 0 = never expires)
API_KEY_EXPIRY_DAYS=365

# Allow API keys in query parameters (less secure, useful for webhooks)
API_KEY_ALLOW_QUERY_PARAM=false

# Rate limiting per API key (requests per minute)
API_KEY_RATE_LIMIT=100

# -----------------------------------------------------------------------------
# JWT CONFIGURATION (Advanced)
# -----------------------------------------------------------------------------
# JWT authentication settings
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# JWT issuer and audience
JWT_ISSUER=graphrag-api
JWT_AUDIENCE=graphrag-users
```

#### Deployment Scenarios

**1. Local Development (No Auth)**
```env
AUTH_MODE=none
AUTH_ENABLED=false
```

**2. Local Development (Simple Auth)**
```env
AUTH_MODE=api_key
DEFAULT_ADMIN_API_KEY=dev_key_123
AUTO_CREATE_ADMIN=true
```

**3. Production (API Key Only)**
```env
AUTH_MODE=api_key
AUTH_ENABLED=true
DEFAULT_ADMIN_API_KEY=${ADMIN_API_KEY_FROM_SECRETS}
AUTO_CREATE_ADMIN=false
API_KEY_ALLOW_QUERY_PARAM=false
API_KEY_RATE_LIMIT=60
```

**4. Enterprise (Full Security)**
```env
AUTH_MODE=both
AUTH_ENABLED=true
AUTO_CREATE_ADMIN=false
JWT_SECRET_KEY=${JWT_SECRET_FROM_VAULT}
API_KEY_PREFIX=grag_prod_
API_KEY_EXPIRY_DAYS=90
API_KEY_RATE_LIMIT=30
```

## Migration Path

For existing users:

1. **Phase 1**: JWT still works, API keys optional
2. **Phase 2**: Recommend API keys in docs
3. **Phase 3**: Deprecation notice for complex JWT flows
4. **Phase 4**: JWT for admin only, API keys for API access

## Testing Strategy

### Unit Tests
- API key generation and validation
- JWT token verification
- Permission checks
- Rate limiting

### Integration Tests
- Full auth flow for both methods
- Provider authentication
- Security headers
- CORS behavior

### Security Tests
- Penetration testing
- Token/key rotation
- Brute force protection
- SQL injection in auth endpoints

## Documentation Deliverables

1. **README.md** - Quick start section
2. **AUTH.md** - Complete authentication guide
3. **PROVIDERS.md** - Provider-specific setup
4. **API_REFERENCE.md** - All auth endpoints
5. **MIGRATION.md** - Moving from JWT to API keys
6. **SECURITY.md** - Security best practices

## Timeline Summary

- **Week 1**: Core JWT completion + API key design
- **Week 2**: API key implementation + GraphRAG integration
- **Week 3**: Documentation + security + testing

Total effort: ~120 hours (3 developers × 1 week each)

## Next Steps

1. Review and approve plan
2. Create feature branch `feature/simplified-auth`
3. Start with Phase 1.1 (wire existing JWT)
4. Daily progress updates
5. Security review before merge