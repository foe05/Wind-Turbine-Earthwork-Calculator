"""
JWT Token Blacklist Management mit Redis

Blacklist-Strategie:
- Redis: Blacklisted JWT tokens mit automatischem TTL
- TTL entspricht der JWT-Ablaufzeit (24 Stunden default)
- Automatische Bereinigung durch Redis EXPIRE
"""
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
import redis
from jose import jwt, JWTError

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """JWT Token Blacklist Manager mit Redis"""

    def __init__(self, redis_url: str, jwt_secret: str, jwt_algorithm: str = "HS256"):
        """
        Initialize token blacklist

        Args:
            redis_url: Redis connection URL
            jwt_secret: JWT secret for decoding tokens
            jwt_algorithm: JWT algorithm (default: HS256)
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm

        logger.info(f"Token Blacklist initialisiert: Redis={redis_url}")

    def _get_blacklist_key(self, token: str) -> str:
        """
        Generate Redis key for blacklisted token

        Format: auth:blacklist:{token_hash}

        Args:
            token: JWT token string

        Returns:
            Redis key string
        """
        # Use first 32 chars of token as identifier (enough for uniqueness)
        token_id = token[:32] if len(token) > 32 else token
        return f"auth:blacklist:{token_id}"

    def _get_token_ttl(self, token: str) -> int:
        """
        Extract TTL from JWT token expiration

        Args:
            token: JWT token string

        Returns:
            TTL in seconds, or default 24h if extraction fails
        """
        try:
            # Decode without verification (we just need expiration)
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_signature": False}
            )

            if "exp" in payload:
                exp_timestamp = payload["exp"]
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                now = datetime.utcnow()

                # Calculate remaining seconds until expiration
                ttl = int((exp_datetime - now).total_seconds())

                # Ensure TTL is positive
                return max(ttl, 60)  # Minimum 1 minute

        except (JWTError, Exception) as e:
            logger.warning(f"TTL-Extraktion fehlgeschlagen: {e}")

        # Default: 24 hours
        return 86400

    def add_to_blacklist(self, token: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Add JWT token to blacklist

        Args:
            token: JWT token string
            ttl_seconds: Optional TTL in seconds (default: extracted from token)

        Returns:
            True if successful
        """
        key = self._get_blacklist_key(token)

        try:
            # Use token's expiration time as TTL if not provided
            if ttl_seconds is None:
                ttl_seconds = self._get_token_ttl(token)

            # Store blacklisted token with metadata
            blacklist_data = {
                "blacklisted_at": datetime.utcnow().isoformat(),
                "expires_at": (
                    datetime.utcnow() + timedelta(seconds=ttl_seconds)
                ).isoformat()
            }

            # Store in Redis with TTL (value is timestamp for debugging)
            self.redis_client.setex(
                key,
                ttl_seconds,
                blacklist_data["blacklisted_at"]
            )

            logger.info(f"  🚫 Token zur Blacklist hinzugefügt: TTL={ttl_seconds}s")

            return True

        except Exception as e:
            logger.error(f"Blacklist-Add-Fehler: {e}")
            return False

    def is_blacklisted(self, token: str) -> bool:
        """
        Check if JWT token is blacklisted

        Args:
            token: JWT token string

        Returns:
            True if token is blacklisted
        """
        key = self._get_blacklist_key(token)

        try:
            # Check if key exists in Redis
            exists = self.redis_client.exists(key)

            if exists:
                logger.info("  🚫 Token ist auf Blacklist")
                return True

            return False

        except Exception as e:
            logger.error(f"Blacklist-Check-Fehler: {e}")
            # Fail-open: If Redis is down, allow the request
            # (JWT signature validation still happens)
            return False

    def get_blacklist_stats(self) -> Dict:
        """
        Get blacklist statistics

        Returns:
            Dict with blacklist stats
        """
        try:
            info = self.redis_client.info()

            # Count blacklisted tokens
            blacklist_keys = self.redis_client.keys("auth:blacklist:*")
            token_count = len(blacklist_keys) if blacklist_keys else 0

            return {
                "redis": {
                    "connected": True,
                    "used_memory_human": info.get("used_memory_human", "N/A"),
                    "blacklisted_tokens": token_count
                },
                "status": "operational"
            }

        except Exception as e:
            logger.error(f"Blacklist-Stats-Fehler: {e}")
            return {
                "redis": {
                    "connected": False,
                    "error": str(e)
                },
                "status": "error"
            }

    def health_check(self) -> bool:
        """
        Check Redis connection health

        Returns:
            True if Redis is reachable
        """
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis Health-Check fehlgeschlagen: {e}")
            return False
