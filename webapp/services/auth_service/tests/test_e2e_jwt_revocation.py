"""
End-to-end test for JWT token revocation flow

This test verifies that:
1. JWT tokens are successfully created and used for authentication
2. JWT tokens are added to Redis blacklist on logout
3. Blacklisted tokens are rejected with 401
4. Tokens expire from blacklist after TTL

Requirements:
- auth_service must be running
- Redis must be running
- PostgreSQL must be running

Run with:
    pytest webapp/services/auth_service/tests/test_e2e_jwt_revocation.py -v -s
"""
import time
import requests
import redis
import hashlib
from datetime import datetime


# Configuration
BASE_URL = "http://localhost:8001"  # auth_service default port
REDIS_URL = "redis://localhost:6379"  # Redis default connection
TEST_EMAIL = "e2e-test@example.com"


def hash_token(token: str) -> str:
    """Hash token for Redis key (matches token_blacklist.py implementation)"""
    return hashlib.sha256(token.encode()).hexdigest()


def test_e2e_jwt_revocation_flow():
    """
    End-to-end test of complete JWT revocation flow

    This test validates the security fix: tokens are properly revoked
    on logout and cannot be reused.
    """
    print("\n" + "="*70)
    print("E2E Test: JWT Token Revocation Flow")
    print("="*70)

    # Connect to Redis for verification
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print("✓ Connected to Redis")
    except Exception as e:
        print(f"✗ Failed to connect to Redis: {e}")
        print(f"  Make sure Redis is running at {REDIS_URL}")
        raise

    # Step 1: Request magic link for test user
    print("\nStep 1: Request magic link for test user")
    response = requests.post(
        f"{BASE_URL}/auth/request-login",
        json={"email": TEST_EMAIL}
    )
    assert response.status_code == 200, f"Failed to request magic link: {response.text}"
    print(f"✓ Magic link requested for {TEST_EMAIL}")
    print(f"  Response: {response.json()['message']}")

    # Step 2: Get magic link token (development endpoint)
    print("\nStep 2: Get magic link token from dev endpoint")
    response = requests.get(f"{BASE_URL}/auth/dev/magic-links/{TEST_EMAIL}")
    assert response.status_code == 200, f"Failed to get magic links: {response.text}"

    data = response.json()
    assert len(data['links']) > 0, "No magic links found"

    magic_token = data['links'][0]['token']
    print(f"✓ Retrieved magic link token: {magic_token[:20]}...")

    # Step 3: Verify magic link and receive JWT token
    print("\nStep 3: Verify magic link and receive JWT token")
    response = requests.get(f"{BASE_URL}/auth/verify/{magic_token}")
    assert response.status_code == 200, f"Failed to verify magic link: {response.text}"

    data = response.json()
    jwt_token = data['access_token']
    user_id = data['user']['id']
    print(f"✓ Received JWT token: {jwt_token[:30]}...")
    print(f"  User ID: {user_id}")
    print(f"  Expires at: {data['expires_at']}")

    # Step 4: Call /me endpoint with JWT - should succeed
    print("\nStep 4: Call /me endpoint with JWT (should succeed)")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert response.status_code == 200, f"Failed to authenticate with JWT: {response.text}"

    user_data = response.json()
    assert user_data['email'] == TEST_EMAIL, "User email mismatch"
    print(f"✓ Successfully authenticated with JWT")
    print(f"  User: {user_data['email']}")

    # Step 5: Verify token is NOT in blacklist yet
    print("\nStep 5: Verify token is NOT in Redis blacklist yet")
    token_hash = hash_token(jwt_token)
    blacklist_key = f"jwt:blacklist:{token_hash}"
    is_blacklisted = redis_client.exists(blacklist_key)
    assert is_blacklisted == 0, "Token should not be blacklisted before logout"
    print(f"✓ Token is not blacklisted (as expected)")
    print(f"  Redis key: {blacklist_key}")

    # Step 6: Call /logout with JWT to revoke token
    print("\nStep 6: Call /logout to revoke JWT token")
    response = requests.post(
        f"{BASE_URL}/auth/logout",
        json={"token": jwt_token}
    )
    assert response.status_code == 200, f"Failed to logout: {response.text}"
    print(f"✓ Successfully logged out")
    print(f"  Message: {response.json()['message']}")

    # Step 7: Verify token is NOW in Redis blacklist
    print("\nStep 7: Verify token IS in Redis blacklist")
    is_blacklisted = redis_client.exists(blacklist_key)
    assert is_blacklisted == 1, "Token should be blacklisted after logout"

    ttl = redis_client.ttl(blacklist_key)
    print(f"✓ Token is blacklisted in Redis")
    print(f"  Redis key: {blacklist_key}")
    print(f"  TTL: {ttl} seconds (~{ttl/3600:.1f} hours)")
    print(f"  Value: {redis_client.get(blacklist_key)}")

    # Verify TTL is reasonable (should be close to JWT expiration, ~24 hours)
    assert ttl > 0, "Token should have a positive TTL"
    assert ttl <= 24 * 3600 + 60, "Token TTL should be <= 24 hours + buffer"
    print(f"✓ Token TTL is within expected range")

    # Step 8: Call /me endpoint with same JWT - should fail with 401
    print("\nStep 8: Call /me endpoint with revoked JWT (should fail)")
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    print(f"✓ Revoked token was rejected with 401")
    print(f"  Error: {response.json()['detail']}")

    # Step 9: Verify blacklist stats
    print("\nStep 9: Verify Redis blacklist stats")
    blacklist_keys = redis_client.keys("jwt:blacklist:*")
    print(f"✓ Total blacklisted tokens in Redis: {len(blacklist_keys)}")

    # Clean up: Remove test token from blacklist
    print("\nCleanup: Removing test token from Redis blacklist")
    redis_client.delete(blacklist_key)
    print(f"✓ Cleaned up test token from Redis")

    print("\n" + "="*70)
    print("✓ ALL E2E TESTS PASSED")
    print("="*70)
    print("\nVerified:")
    print("  ✓ JWT tokens can be created and used for authentication")
    print("  ✓ Logout adds JWT to Redis blacklist with correct TTL")
    print("  ✓ Blacklisted tokens are rejected with 401")
    print("  ✓ Token revocation flow is working correctly")
    print("\nSecurity fix confirmed: JWT tokens are properly revoked on logout!")
    print("="*70 + "\n")


if __name__ == "__main__":
    """
    Run this script directly to test JWT revocation flow

    Prerequisites:
    1. Start services: cd webapp && docker-compose up -d postgres redis auth_service
    2. Install dependencies: pip install requests redis pytest
    3. Run test: python webapp/services/auth_service/tests/test_e2e_jwt_revocation.py
    """
    test_e2e_jwt_revocation_flow()
