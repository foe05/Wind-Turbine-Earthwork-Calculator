"""
Unit tests for JWT Token Blacklist Module

Tests cover:
- Token blacklisting operations
- TTL extraction from JWT
- Redis connection error handling
- Blacklist statistics and health checks
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from jose import jwt

# Import the module under test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.token_blacklist import TokenBlacklist


class TestTokenBlacklist:
    """Test suite for TokenBlacklist class"""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        with patch('app.core.token_blacklist.redis') as mock_redis_module:
            mock_client = MagicMock()
            mock_redis_module.from_url.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def blacklist(self, mock_redis):
        """Create a TokenBlacklist instance with mocked Redis"""
        return TokenBlacklist(
            redis_url="redis://localhost:6379",
            jwt_secret="test-secret-key",
            jwt_algorithm="HS256"
        )

    @pytest.fixture
    def valid_jwt_token(self):
        """Create a valid JWT token with expiration"""
        secret = "test-secret-key"
        expiration = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "sub": "user123",
            "exp": expiration.timestamp()
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        return token

    @pytest.fixture
    def expired_jwt_token(self):
        """Create an expired JWT token"""
        secret = "test-secret-key"
        expiration = datetime.utcnow() - timedelta(hours=1)
        payload = {
            "sub": "user123",
            "exp": expiration.timestamp()
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        return token

    # Test: Initialization
    def test_init(self, mock_redis):
        """Test TokenBlacklist initialization"""
        blacklist = TokenBlacklist(
            redis_url="redis://localhost:6379",
            jwt_secret="test-secret",
            jwt_algorithm="HS256"
        )

        assert blacklist.jwt_secret == "test-secret"
        assert blacklist.jwt_algorithm == "HS256"
        assert blacklist.redis_client is not None

    # Test: Get blacklist key
    def test_get_blacklist_key(self, blacklist):
        """Test Redis key generation for blacklisted tokens"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        key = blacklist._get_blacklist_key(token)

        assert key.startswith("auth:blacklist:")
        assert len(key) > len("auth:blacklist:")

    def test_get_blacklist_key_short_token(self, blacklist):
        """Test Redis key generation for short tokens"""
        token = "short_token"
        key = blacklist._get_blacklist_key(token)

        assert key == "auth:blacklist:short_token"

    # Test: Get token TTL
    def test_get_token_ttl_valid_jwt(self, blacklist, valid_jwt_token):
        """Test TTL extraction from valid JWT token"""
        ttl = blacklist._get_token_ttl(valid_jwt_token)

        # TTL should be roughly 1 hour (3600 seconds)
        assert 3500 <= ttl <= 3700

    def test_get_token_ttl_expired_jwt(self, blacklist, expired_jwt_token):
        """Test TTL extraction from expired JWT (should return minimum TTL)"""
        ttl = blacklist._get_token_ttl(expired_jwt_token)

        # Should return minimum TTL of 60 seconds
        assert ttl == 60

    def test_get_token_ttl_invalid_jwt(self, blacklist):
        """Test TTL extraction from invalid JWT (should return default)"""
        invalid_token = "invalid.jwt.token"
        ttl = blacklist._get_token_ttl(invalid_token)

        # Should return default TTL of 24 hours (86400 seconds)
        assert ttl == 86400

    def test_get_token_ttl_no_exp_claim(self, blacklist):
        """Test TTL extraction from JWT without exp claim"""
        secret = "test-secret-key"
        payload = {"sub": "user123"}  # No exp claim
        token = jwt.encode(payload, secret, algorithm="HS256")

        ttl = blacklist._get_token_ttl(token)

        # Should return default TTL of 24 hours
        assert ttl == 86400

    # Test: Add to blacklist
    def test_add_to_blacklist_success(self, blacklist, mock_redis, valid_jwt_token):
        """Test successful token blacklisting"""
        mock_redis.setex.return_value = True

        result = blacklist.add_to_blacklist(valid_jwt_token)

        assert result is True
        mock_redis.setex.assert_called_once()

        # Verify setex was called with correct parameters
        call_args = mock_redis.setex.call_args
        key = call_args[0][0]
        ttl = call_args[0][1]
        value = call_args[0][2]

        assert key.startswith("auth:blacklist:")
        assert ttl > 0
        assert isinstance(value, str)

    def test_add_to_blacklist_custom_ttl(self, blacklist, mock_redis, valid_jwt_token):
        """Test blacklisting with custom TTL"""
        mock_redis.setex.return_value = True
        custom_ttl = 300

        result = blacklist.add_to_blacklist(valid_jwt_token, ttl_seconds=custom_ttl)

        assert result is True

        # Verify custom TTL was used
        call_args = mock_redis.setex.call_args
        ttl = call_args[0][1]
        assert ttl == custom_ttl

    def test_add_to_blacklist_redis_error(self, blacklist, mock_redis, valid_jwt_token):
        """Test blacklisting when Redis connection fails"""
        mock_redis.setex.side_effect = Exception("Redis connection error")

        result = blacklist.add_to_blacklist(valid_jwt_token)

        assert result is False

    # Test: Is blacklisted
    def test_is_blacklisted_true(self, blacklist, mock_redis, valid_jwt_token):
        """Test checking if token is blacklisted (token exists)"""
        mock_redis.exists.return_value = 1

        result = blacklist.is_blacklisted(valid_jwt_token)

        assert result is True
        mock_redis.exists.assert_called_once()

    def test_is_blacklisted_false(self, blacklist, mock_redis, valid_jwt_token):
        """Test checking if token is not blacklisted"""
        mock_redis.exists.return_value = 0

        result = blacklist.is_blacklisted(valid_jwt_token)

        assert result is False

    def test_is_blacklisted_redis_error(self, blacklist, mock_redis, valid_jwt_token):
        """Test blacklist check when Redis fails (fail-open strategy)"""
        mock_redis.exists.side_effect = Exception("Redis connection error")

        result = blacklist.is_blacklisted(valid_jwt_token)

        # Should fail-open (return False) to allow JWT validation
        assert result is False

    # Test: Get blacklist stats
    def test_get_blacklist_stats_success(self, blacklist, mock_redis):
        """Test retrieving blacklist statistics"""
        mock_redis.info.return_value = {
            "used_memory_human": "1.5M"
        }
        mock_redis.keys.return_value = [
            "auth:blacklist:token1",
            "auth:blacklist:token2"
        ]

        stats = blacklist.get_blacklist_stats()

        assert stats["status"] == "operational"
        assert stats["redis"]["connected"] is True
        assert stats["redis"]["used_memory_human"] == "1.5M"
        assert stats["redis"]["blacklisted_tokens"] == 2

    def test_get_blacklist_stats_no_tokens(self, blacklist, mock_redis):
        """Test statistics when no tokens are blacklisted"""
        mock_redis.info.return_value = {
            "used_memory_human": "1.0M"
        }
        mock_redis.keys.return_value = []

        stats = blacklist.get_blacklist_stats()

        assert stats["redis"]["blacklisted_tokens"] == 0

    def test_get_blacklist_stats_redis_error(self, blacklist, mock_redis):
        """Test statistics retrieval when Redis fails"""
        mock_redis.info.side_effect = Exception("Redis connection error")

        stats = blacklist.get_blacklist_stats()

        assert stats["status"] == "error"
        assert stats["redis"]["connected"] is False
        assert "error" in stats["redis"]

    # Test: Health check
    def test_health_check_success(self, blacklist, mock_redis):
        """Test Redis health check when connection is healthy"""
        mock_redis.ping.return_value = True

        result = blacklist.health_check()

        assert result is True
        mock_redis.ping.assert_called_once()

    def test_health_check_failure(self, blacklist, mock_redis):
        """Test Redis health check when connection fails"""
        mock_redis.ping.side_effect = Exception("Connection refused")

        result = blacklist.health_check()

        assert result is False

    # Integration-style tests
    def test_blacklist_workflow(self, blacklist, mock_redis, valid_jwt_token):
        """Test complete blacklist workflow: add -> check -> verify"""
        # Setup mocks
        mock_redis.setex.return_value = True
        mock_redis.exists.return_value = 1

        # Add token to blacklist
        add_result = blacklist.add_to_blacklist(valid_jwt_token)
        assert add_result is True

        # Check if token is blacklisted
        is_blacklisted = blacklist.is_blacklisted(valid_jwt_token)
        assert is_blacklisted is True

    def test_ttl_expiration_simulation(self, blacklist, mock_redis, valid_jwt_token):
        """Test that TTL is properly set for automatic expiration"""
        mock_redis.setex.return_value = True

        # Add token with short TTL
        blacklist.add_to_blacklist(valid_jwt_token, ttl_seconds=60)

        # Verify setex was called with 60 second TTL
        call_args = mock_redis.setex.call_args
        ttl = call_args[0][1]
        assert ttl == 60


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
