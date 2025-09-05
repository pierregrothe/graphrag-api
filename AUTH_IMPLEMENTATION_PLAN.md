# Authentication Implementation Plan

## Overview

This plan addresses the TODO comments in `src/graphrag_api_service/routes/auth.py` that are blocking commits due to pre-commit hooks. The implementation will add proper database integration for authentication functionality.

## Current TODOs to Address

1. Database check for user existence
2. Database insertion for user registration
3. Database authentication for login
4. Database update for user profile changes

## Implementation Phases

### Phase 1: Database Schema and Models

**Objective**: Establish database foundation for authentication

#### Tasks

1. **Create User Model** (`src/graphrag_api_service/models/user.py`)
    - User ID (UUID)
    - Username (unique, indexed)
    - Email (unique, indexed)
    - Password hash
    - Created/Updated timestamps
    - Is_active flag
    - Role/permissions

2. **Extend SQLite Manager** (`src/graphrag_api_service/database/sqlite_models.py`)
    - Add users table creation
    - Add user CRUD operations
    - Add password hashing utilities
    - Add session/token management table

3. **Create Database Migration Script**
    - Initialize users table
    - Add indexes for performance
    - Set up default admin user (optional)

### Phase 2: Authentication Service Layer

**Objective**: Implement business logic for authentication

#### Tasks

1. **Create Auth Service** (`src/graphrag_api_service/services/auth_service.py`)
    - User registration logic
    - User authentication logic
    - Password hashing/verification (using passlib)
    - Token generation and validation
    - User session management

2. **Create User Repository** (`src/graphrag_api_service/repositories/user_repository.py`)
    - Get user by username
    - Get user by email
    - Create new user
    - Update user profile
    - Delete user
    - Check user existence

3. **Add Security Utilities** (`src/graphrag_api_service/utils/security.py`)
    - Password strength validation
    - Input sanitization
    - Rate limiting helpers

### Phase 3: Update Auth Routes

**Objective**: Replace TODOs with actual implementation

#### Tasks

1. **Update `/auth/check-user` endpoint**

    ```python
    # Replace: # TODO: Implement actual database check
    # With: Actual database lookup using user repository
    user_exists = await user_repository.check_user_exists(username)
    ```

2. **Update `/auth/register` endpoint**

    ```python
    # Replace: # TODO: Implement actual database insertion
    # With: User creation with proper validation
    new_user = await auth_service.register_user(user_data)
    ```

3. **Update `/auth/login` endpoint**

    ```python
    # Replace: # TODO: Implement actual database authentication
    # With: Authentication and token generation
    auth_result = await auth_service.authenticate(credentials)
    ```

4. **Update `/auth/profile` endpoint**

    ```python
    # Replace: # TODO: Implement actual database update
    # With: Profile update with validation
    updated_user = await user_repository.update_user(user_id, profile_data)
    ```

### Phase 4: Testing

**Objective**: Ensure robust authentication system

#### Tasks

1. **Unit Tests** (`tests/unit/test_auth_service.py`)
    - Test user registration
    - Test authentication
    - Test password hashing
    - Test token generation/validation
    - Test input validation

2. **Integration Tests** (`tests/integration/test_auth_routes.py`)
    - Test complete registration flow
    - Test login/logout flow
    - Test profile update flow
    - Test error cases

3. **Security Tests**
    - Test SQL injection prevention
    - Test password strength requirements
    - Test rate limiting
    - Test token expiration

### Phase 5: Code Quality and Documentation

**Objective**: Ensure production readiness

#### Tasks

1. **Code Quality Checks**

    ```bash
    poetry run black src/ tests/
    poetry run ruff check src/ tests/
    poetry run mypy src/graphrag_api_service
    poetry run bandit -r src/ -ll
    ```

2. **Documentation Updates**
    - Update API documentation
    - Add authentication flow diagrams
    - Document security considerations
    - Update README with auth setup

3. **Configuration Updates**
    - Add auth-related environment variables
    - Update `.env.example`
    - Add JWT configuration options

## Dependencies to Add

```toml
# Already in pyproject.toml:
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}

# May need to add:
email-validator = "^2.0.0"  # For email validation
python-multipart = "^0.0.6"  # For form data handling
```

## Environment Variables Needed

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Security
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
```

## File Structure After Implementation

```
src/graphrag_api_service/
├── models/
│   └── user.py              # User model
├── services/
│   └── auth_service.py      # Authentication logic
├── repositories/
│   └── user_repository.py   # Database operations
├── utils/
│   └── security.py          # Security utilities
├── routes/
│   └── auth.py             # Updated without TODOs
└── database/
    └── sqlite_models.py     # Extended with user tables

tests/
├── unit/
│   └── test_auth_service.py
└── integration/
    └── test_auth_routes.py
```

## Success Criteria

1. All TODO comments removed from production code
2. All authentication endpoints functional
3. All tests passing (unit and integration)
4. Code quality checks passing (Black, Ruff, MyPy, Bandit)
5. Pre-commit hooks passing
6. CI/CD pipeline green

## Risk Mitigation

- **Security**: Use established libraries (passlib, python-jose)
- **Performance**: Add database indexes for user lookups
- **Compatibility**: Maintain backward compatibility with existing code
- **Testing**: Comprehensive test coverage before deployment

## Timeline Estimate

- Phase 1: 2-3 hours (Database setup)
- Phase 2: 3-4 hours (Service layer)
- Phase 3: 2-3 hours (Route updates)
- Phase 4: 2-3 hours (Testing)
- Phase 5: 1-2 hours (Quality & docs)

**Total: 10-15 hours of development**

## Notes

- Consider using FastAPI's built-in security utilities
- Ensure all database operations are async
- Add proper logging for security events
- Consider implementing refresh tokens for better UX
- Plan for future OAuth2/SSO integration
