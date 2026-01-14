# End-to-End Verification: JWT Token Revocation

This directory contains comprehensive E2E tests to verify the JWT token revocation feature.

## Overview

The JWT revocation feature ensures that tokens are properly blacklisted in Redis when users log out, preventing their reuse even before natural expiration.

## Test Files

1. **`test_e2e_jwt_revocation.py`** - Automated pytest test
2. **`manual_e2e_verification.sh`** - Manual bash script with curl
3. **`E2E_VERIFICATION_README.md`** - This file

## Prerequisites

Before running tests, ensure services are running:

```bash
# Start required services
cd webapp
docker-compose up -d postgres redis auth_service

# Verify services are running
docker-compose ps

# Check logs if needed
docker-compose logs auth_service
docker-compose logs redis
```

## Option 1: Automated Python Test (Recommended)

### Setup

```bash
# Install dependencies
pip install requests redis pytest

# Or install from requirements
cd webapp/services/auth_service
pip install -r requirements.txt
pip install requests redis  # These might not be in requirements
```

### Run Test

```bash
# From project root
pytest webapp/services/auth_service/tests/test_e2e_jwt_revocation.py -v -s

# Or run directly as a script
python webapp/services/auth_service/tests/test_e2e_jwt_revocation.py
```

### Expected Output

```
==================================================================
E2E Test: JWT Token Revocation Flow
==================================================================

✓ Connected to Redis

Step 1: Request magic link for test user
✓ Magic link requested for e2e-test@example.com

Step 2: Get magic link token from dev endpoint
✓ Retrieved magic link token: abc123...

Step 3: Verify magic link and receive JWT token
✓ Received JWT token: eyJhbGciOiJIUzI1NiIsInR5cCI6...
  User ID: 123e4567-e89b-12d3-a456-426614174000
  Expires at: 2026-01-15T20:00:00

Step 4: Call /me endpoint with JWT (should succeed)
✓ Successfully authenticated with JWT
  User: e2e-test@example.com

Step 5: Verify token is NOT in Redis blacklist yet
✓ Token is not blacklisted (as expected)
  Redis key: jwt:blacklist:abc123...

Step 6: Call /logout to revoke JWT token
✓ Successfully logged out
  Message: Successfully logged out

Step 7: Verify token IS in Redis blacklist
✓ Token is blacklisted in Redis
  Redis key: jwt:blacklist:abc123...
  TTL: 86340 seconds (~24.0 hours)
  Value: revoked

Step 8: Call /me endpoint with revoked JWT (should fail)
✓ Revoked token was rejected with 401
  Error: Invalid token

Step 9: Verify Redis blacklist stats
✓ Total blacklisted tokens in Redis: 5

Cleanup: Removing test token from Redis blacklist
✓ Cleaned up test token from Redis

==================================================================
✓ ALL E2E TESTS PASSED
==================================================================

Verified:
  ✓ JWT tokens can be created and used for authentication
  ✓ Logout adds JWT to Redis blacklist with correct TTL
  ✓ Blacklisted tokens are rejected with 401
  ✓ Token revocation flow is working correctly

Security fix confirmed: JWT tokens are properly revoked on logout!
==================================================================
```

## Option 2: Manual Bash Script

### Requirements

- `curl` - for API calls
- `redis-cli` - for Redis verification
- `jq` - for JSON parsing (optional, for pretty output)

### Run Test

```bash
# Make script executable (if not already)
chmod +x webapp/services/auth_service/tests/manual_e2e_verification.sh

# Run the script
./webapp/services/auth_service/tests/manual_e2e_verification.sh
```

### Expected Output

Similar to automated test, but with curl commands and JSON responses displayed.

## Verification Steps

Both tests perform the following verification flow:

### 1. Request Magic Link
- **Endpoint**: `POST /auth/request-login`
- **Purpose**: Create a magic link for test user
- **Expected**: 200 OK with success message

### 2. Get Magic Link Token
- **Endpoint**: `GET /auth/dev/magic-links/{email}`
- **Purpose**: Retrieve magic link token (dev only)
- **Expected**: 200 OK with token array

### 3. Verify Magic Link
- **Endpoint**: `GET /auth/verify/{token}`
- **Purpose**: Exchange magic link for JWT
- **Expected**: 200 OK with JWT access token

### 4. Authenticate with JWT
- **Endpoint**: `GET /auth/me`
- **Headers**: `Authorization: Bearer {jwt}`
- **Purpose**: Verify JWT works for authentication
- **Expected**: 200 OK with user data

### 5. Check Blacklist Before Logout
- **Redis**: `EXISTS jwt:blacklist:{token_hash}`
- **Purpose**: Confirm token is NOT blacklisted yet
- **Expected**: Key does not exist (0)

### 6. Logout and Revoke Token
- **Endpoint**: `POST /auth/logout`
- **Body**: `{"token": "{jwt}"}`
- **Purpose**: Revoke JWT by adding to blacklist
- **Expected**: 200 OK with logout message

### 7. Verify Token in Blacklist
- **Redis**: `EXISTS jwt:blacklist:{token_hash}`
- **Redis**: `TTL jwt:blacklist:{token_hash}`
- **Purpose**: Confirm token IS blacklisted
- **Expected**: Key exists (1) with TTL ≈ 24 hours

### 8. Attempt to Use Revoked Token
- **Endpoint**: `GET /auth/me`
- **Headers**: `Authorization: Bearer {jwt}`
- **Purpose**: Verify revoked token is rejected
- **Expected**: **401 Unauthorized** ⚠️

### 9. Check Blacklist Stats
- **Redis**: `KEYS jwt:blacklist:*`
- **Purpose**: View all blacklisted tokens
- **Expected**: List of blacklisted token keys

## Troubleshooting

### Services Not Running

```bash
# Check service status
cd webapp
docker-compose ps

# Start services if not running
docker-compose up -d postgres redis auth_service

# Check logs
docker-compose logs -f auth_service
```

### Connection Errors

```bash
# Test auth_service
curl http://localhost:8001/health

# Test Redis
redis-cli ping
# Should return: PONG
```

### Port Conflicts

If default ports are in use, update the test scripts:
- Auth service: Change `BASE_URL` (default: http://localhost:8001)
- Redis: Change `REDIS_URL` (default: redis://localhost:6379)

### Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Test connection
redis-cli -h localhost -p 6379 ping
```

### Token Already Blacklisted

If you see "Token is already in blacklist" during step 5:

```bash
# Clear all blacklisted tokens
redis-cli KEYS "jwt:blacklist:*" | xargs redis-cli DEL

# Or delete specific token
redis-cli DEL "jwt:blacklist:{token_hash}"
```

## Manual Testing with curl

If you prefer to run commands manually:

```bash
# 1. Request login
curl -X POST http://localhost:8001/auth/request-login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# 2. Get magic link (dev endpoint)
curl http://localhost:8001/auth/dev/magic-links/test@example.com

# 3. Verify magic link (use token from step 2)
curl http://localhost:8001/auth/verify/{MAGIC_TOKEN}

# 4. Test authentication (use JWT from step 3)
curl http://localhost:8001/auth/me \
  -H "Authorization: Bearer {JWT_TOKEN}"

# 5. Check Redis (use JWT from step 3)
TOKEN_HASH=$(echo -n "{JWT_TOKEN}" | sha256sum | awk '{print $1}')
redis-cli EXISTS "jwt:blacklist:${TOKEN_HASH}"

# 6. Logout
curl -X POST http://localhost:8001/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"token": "{JWT_TOKEN}"}'

# 7. Verify in Redis
redis-cli EXISTS "jwt:blacklist:${TOKEN_HASH}"
redis-cli TTL "jwt:blacklist:${TOKEN_HASH}"
redis-cli GET "jwt:blacklist:${TOKEN_HASH}"

# 8. Try using revoked token (should fail with 401)
curl http://localhost:8001/auth/me \
  -H "Authorization: Bearer {JWT_TOKEN}"
```

## Success Criteria

All tests MUST pass for the feature to be considered working:

- ✅ JWT tokens are created successfully
- ✅ JWT tokens work for authentication before logout
- ✅ Logout adds JWT to Redis blacklist
- ✅ Blacklisted tokens have correct TTL (≈ 24 hours)
- ✅ Blacklisted tokens are rejected with 401
- ✅ Redis connection failures are handled gracefully (fail-open)

## Security Validation

This E2E test validates the security fix for:

**Issue**: JWT tokens remained valid after logout, allowing potential misuse on shared/public computers.

**Fix**: JWT tokens are now added to a Redis blacklist on logout and rejected by `verify_token()`, providing true revocation capability.

**Risk Mitigation**: Even if Redis is unavailable, the system fails open (allows authentication) to prevent service disruption, but logs warnings for monitoring.

## Next Steps

After successful E2E verification:

1. ✅ Mark subtask-3-2 as completed in implementation_plan.json
2. ✅ Commit changes with descriptive message
3. ✅ Update build-progress.txt
4. ✅ Run QA acceptance tests
5. ✅ Request QA sign-off

## Additional Resources

- **Implementation**: `webapp/services/auth_service/app/core/token_blacklist.py`
- **Security Module**: `webapp/services/auth_service/app/core/security.py`
- **Auth Endpoints**: `webapp/services/auth_service/app/api/auth.py`
- **Unit Tests**: `webapp/services/auth_service/tests/test_token_blacklist.py`
- **Spec**: `.auto-claude/specs/017-jwt-tokens-cannot-be-revoked-after-logout/spec.md`
- **Implementation Plan**: `.auto-claude/specs/017-jwt-tokens-cannot-be-revoked-after-logout/implementation_plan.json`
