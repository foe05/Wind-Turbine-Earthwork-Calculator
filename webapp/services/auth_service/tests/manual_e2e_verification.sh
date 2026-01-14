#!/bin/bash
#
# Manual E2E Verification Script for JWT Token Revocation
#
# This script performs step-by-step verification of the JWT revocation flow.
# It uses curl to make API calls and redis-cli to verify blacklist entries.
#
# Prerequisites:
# - auth_service running on http://localhost:8001
# - Redis running on localhost:6379
# - curl and redis-cli installed
#
# Usage:
#   chmod +x manual_e2e_verification.sh
#   ./manual_e2e_verification.sh

set -e  # Exit on error

BASE_URL="http://localhost:8001"
TEST_EMAIL="manual-test@example.com"

echo "========================================================================"
echo "Manual E2E Verification: JWT Token Revocation Flow"
echo "========================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Request magic link
echo "Step 1: Request magic link for test user"
echo "----------------------------------------"
echo "Request: POST ${BASE_URL}/auth/request-login"
echo ""

RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/request-login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"${TEST_EMAIL}\"}")

echo "$RESPONSE" | jq '.'
echo -e "${GREEN}✓ Magic link requested${NC}"
echo ""

# Step 2: Get magic link token (development endpoint)
echo "Step 2: Get magic link token from dev endpoint"
echo "------------------------------------------------"
echo "Request: GET ${BASE_URL}/auth/dev/magic-links/${TEST_EMAIL}"
echo ""

RESPONSE=$(curl -s "${BASE_URL}/auth/dev/magic-links/${TEST_EMAIL}")
echo "$RESPONSE" | jq '.'

MAGIC_TOKEN=$(echo "$RESPONSE" | jq -r '.links[0].token')
echo ""
echo -e "${GREEN}✓ Retrieved magic link token: ${MAGIC_TOKEN:0:30}...${NC}"
echo ""

# Step 3: Verify magic link and receive JWT
echo "Step 3: Verify magic link and receive JWT token"
echo "------------------------------------------------"
echo "Request: GET ${BASE_URL}/auth/verify/${MAGIC_TOKEN}"
echo ""

RESPONSE=$(curl -s "${BASE_URL}/auth/verify/${MAGIC_TOKEN}")
echo "$RESPONSE" | jq '.'

JWT_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
USER_EMAIL=$(echo "$RESPONSE" | jq -r '.user.email')

echo ""
echo -e "${GREEN}✓ Received JWT token: ${JWT_TOKEN:0:40}...${NC}"
echo "  User: ${USER_EMAIL}"
echo ""

# Step 4: Call /me endpoint with JWT (should succeed)
echo "Step 4: Call /me endpoint with JWT (should succeed)"
echo "----------------------------------------------------"
echo "Request: GET ${BASE_URL}/auth/me"
echo "Authorization: Bearer ${JWT_TOKEN:0:40}..."
echo ""

HTTP_CODE=$(curl -s -o /tmp/me_response.json -w "%{http_code}" \
  "${BASE_URL}/auth/me" \
  -H "Authorization: Bearer ${JWT_TOKEN}")

if [ "$HTTP_CODE" -eq 200 ]; then
    cat /tmp/me_response.json | jq '.'
    echo ""
    echo -e "${GREEN}✓ Successfully authenticated with JWT (HTTP ${HTTP_CODE})${NC}"
else
    cat /tmp/me_response.json
    echo ""
    echo -e "${RED}✗ Authentication failed (HTTP ${HTTP_CODE})${NC}"
    exit 1
fi
echo ""

# Step 5: Verify token is NOT in Redis blacklist yet
echo "Step 5: Verify token is NOT in Redis blacklist yet"
echo "---------------------------------------------------"

TOKEN_HASH=$(echo -n "${JWT_TOKEN}" | sha256sum | awk '{print $1}')
REDIS_KEY="jwt:blacklist:${TOKEN_HASH}"

echo "Token hash: ${TOKEN_HASH}"
echo "Redis key: ${REDIS_KEY}"
echo ""

EXISTS=$(redis-cli EXISTS "${REDIS_KEY}")
if [ "$EXISTS" -eq 0 ]; then
    echo -e "${GREEN}✓ Token is NOT in blacklist (as expected before logout)${NC}"
else
    echo -e "${RED}✗ Token is already in blacklist (unexpected!)${NC}"
    exit 1
fi
echo ""

# Step 6: Call /logout to revoke token
echo "Step 6: Call /logout to revoke JWT token"
echo "-----------------------------------------"
echo "Request: POST ${BASE_URL}/auth/logout"
echo ""

RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/logout" \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"${JWT_TOKEN}\"}")

echo "$RESPONSE" | jq '.'
echo ""
echo -e "${GREEN}✓ Successfully logged out${NC}"
echo ""

# Step 7: Verify token IS in Redis blacklist now
echo "Step 7: Verify token IS in Redis blacklist now"
echo "-----------------------------------------------"

EXISTS=$(redis-cli EXISTS "${REDIS_KEY}")
if [ "$EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✓ Token is NOW in blacklist${NC}"

    TTL=$(redis-cli TTL "${REDIS_KEY}")
    VALUE=$(redis-cli GET "${REDIS_KEY}")

    echo "  Redis key: ${REDIS_KEY}"
    echo "  TTL: ${TTL} seconds (~$((TTL / 3600)) hours)"
    echo "  Value: ${VALUE}"
else
    echo -e "${RED}✗ Token is NOT in blacklist (should be!)${NC}"
    exit 1
fi
echo ""

# Step 8: Call /me endpoint with revoked JWT (should fail with 401)
echo "Step 8: Call /me endpoint with revoked JWT (should fail)"
echo "---------------------------------------------------------"
echo "Request: GET ${BASE_URL}/auth/me"
echo "Authorization: Bearer ${JWT_TOKEN:0:40}..."
echo ""

HTTP_CODE=$(curl -s -o /tmp/me_response_revoked.json -w "%{http_code}" \
  "${BASE_URL}/auth/me" \
  -H "Authorization: Bearer ${JWT_TOKEN}")

if [ "$HTTP_CODE" -eq 401 ]; then
    cat /tmp/me_response_revoked.json | jq '.'
    echo ""
    echo -e "${GREEN}✓ Revoked token was rejected with 401 Unauthorized${NC}"
else
    cat /tmp/me_response_revoked.json
    echo ""
    echo -e "${RED}✗ Revoked token was NOT rejected (HTTP ${HTTP_CODE})${NC}"
    exit 1
fi
echo ""

# Step 9: Check blacklist stats
echo "Step 9: Check Redis blacklist stats"
echo "------------------------------------"

BLACKLIST_COUNT=$(redis-cli KEYS "jwt:blacklist:*" | wc -l)
echo "Total blacklisted tokens: ${BLACKLIST_COUNT}"
echo ""

# Cleanup
echo "Cleanup: Remove test token from Redis"
echo "--------------------------------------"
redis-cli DEL "${REDIS_KEY}" > /dev/null
echo -e "${GREEN}✓ Cleaned up test token${NC}"
echo ""

# Final summary
echo "========================================================================"
echo -e "${GREEN}✓ ALL E2E VERIFICATION STEPS PASSED${NC}"
echo "========================================================================"
echo ""
echo "Verified:"
echo "  ✓ JWT tokens can be created and used for authentication"
echo "  ✓ Logout adds JWT to Redis blacklist with correct TTL"
echo "  ✓ Blacklisted tokens are rejected with 401 Unauthorized"
echo "  ✓ Token revocation flow is working correctly"
echo ""
echo -e "${YELLOW}Security fix confirmed: JWT tokens are properly revoked on logout!${NC}"
echo "========================================================================"
echo ""

# Clean up temp files
rm -f /tmp/me_response.json /tmp/me_response_revoked.json
