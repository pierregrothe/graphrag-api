# Configuration Management

This document explains the configuration architecture of the GraphRAG API service, including the separation between runtime and deployment configurations.

## Configuration Architecture

The GraphRAG API service uses a dual configuration system to separate concerns between runtime application settings and deployment-specific configurations:

### 1. Runtime Configuration (`src/graphrag_api_service/config.py`)

**Purpose**: Application-level settings that control the behavior of the GraphRAG API service during runtime.

**Scope**:

- API behavior settings
- GraphRAG processing parameters
- Default values for application features
- Cross-cutting concerns like logging levels

**Key Settings**:

```python
# API Configuration
app_name: str = "GraphRAG API"
app_version: str = "0.1.0"
debug: bool = False

# GraphRAG Configuration
graphrag_data_path: str = ""
llm_model: str = "gpt-4"
embedding_model: str = "text-embedding-ada-002"
chunk_size: int = 1200
chunk_overlap: int = 100

# Performance Settings
max_concurrent_queries: int = 10
query_timeout: int = 300
```

**Usage**: Imported and used throughout the application code for runtime decisions.

### 2. Deployment Configuration (`src/graphrag_api_service/deployment/config.py`)

**Purpose**: Infrastructure and deployment-specific settings that vary between environments (development, staging, production).

**Scope**:

- Database connection settings
- External service configurations
- Security settings (secrets, keys)
- Environment-specific parameters
- Resource limits and scaling parameters

**Key Settings**:

```python
# Database Configuration
database:
  host: str = "localhost"
  port: int = 5432
  name: str = "graphrag"
  user: str = "postgres"
  password: str = ""
  pool_size: int = 10
  max_overflow: int = 20

# Security Configuration
secret_key: str = ""
jwt_secret_key: str = ""
api_key_encryption_key: str = ""

# External Services
redis:
  host: str = "localhost"
  port: int = 6379
  db: int = 0
```

**Usage**: Used during application initialization and service setup.

## Configuration Loading Strategy

### Environment-Based Loading

Both configuration systems support environment variable overrides:

1. **Runtime Config**: Uses Pydantic's `BaseSettings` with `env_prefix="GRAPHRAG_"`
2. **Deployment Config**: Uses `env_prefix="DEPLOY_"` to avoid conflicts

### Example Environment Variables

```bash
# Runtime Configuration
export GRAPHRAG_DEBUG=true
export GRAPHRAG_LLM_MODEL=gpt-3.5-turbo
export GRAPHRAG_CHUNK_SIZE=800

# Deployment Configuration
export DEPLOY_DATABASE_HOST=prod-db.example.com
export DEPLOY_DATABASE_PASSWORD=secure_password
export DEPLOY_SECRET_KEY=your_secret_key_here
```

### Configuration Precedence

1. **Environment Variables** (highest priority)
2. **Configuration Files** (.env files)
3. **Default Values** (lowest priority)

## Best Practices

### 1. Separation of Concerns

- **Runtime settings** should be application logic decisions
- **Deployment settings** should be infrastructure decisions
- Never mix the two in the same configuration class

### 2. Environment Variable Naming

- Runtime: `GRAPHRAG_*` prefix
- Deployment: `DEPLOY_*` prefix
- Use UPPER_CASE with underscores

### 3. Secret Management

- Never commit secrets to version control
- Use environment variables or secret management systems
- Deployment config handles all sensitive data

### 4. Default Values

- Provide sensible defaults for development
- Production deployments should override all critical settings
- Document required vs optional settings

## Configuration Validation

Both configuration systems include validation:

```python
# Runtime validation
@validator('chunk_size')
def validate_chunk_size(cls, v):
    if v < 100 or v > 5000:
        raise ValueError('chunk_size must be between 100 and 5000')
    return v

# Deployment validation
@validator('database')
def validate_database_config(cls, v):
    if not v.password and v.host != 'localhost':
        raise ValueError('Database password required for non-localhost connections')
    return v
```

## Migration Guide

### From Single Configuration

If migrating from a single configuration file:

1. **Identify Settings**: Categorize each setting as runtime or deployment
2. **Move Settings**: Place in appropriate configuration class
3. **Update Imports**: Change import statements in affected modules
4. **Update Environment Variables**: Rename with appropriate prefixes
5. **Test**: Verify all settings load correctly in each environment

### Example Migration

**Before** (single config):

```python
# config.py
class Settings(BaseSettings):
    app_name: str = "GraphRAG API"
    database_url: str = "postgresql://localhost/graphrag"
    secret_key: str = ""
```

**After** (separated):

```python
# config.py (runtime)
class Settings(BaseSettings):
    app_name: str = "GraphRAG API"

# deployment/config.py (deployment)
class DeploymentSettings(BaseSettings):
    database_url: str = "postgresql://localhost/graphrag"
    secret_key: str = ""
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Check import paths after configuration separation
2. **Missing Environment Variables**: Verify prefix usage (`GRAPHRAG_` vs `DEPLOY_`)
3. **Configuration Not Loading**: Check file paths and environment variable names
4. **Validation Errors**: Review required vs optional settings

### Debugging Configuration

```python
# Debug runtime config
from graphrag_api_service.config import settings
print(settings.dict())

# Debug deployment config
from graphrag_api_service.deployment.config import DeploymentSettings
deploy_settings = DeploymentSettings()
print(deploy_settings.dict())
```

## Related Documentation

- [Environment Setup](ENVIRONMENT.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Security Configuration](SECURITY.md)
