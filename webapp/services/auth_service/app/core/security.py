"""
Security utilities: JWT, Magic Links, Password hashing
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.core.config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Magic link serializer
magic_link_serializer = URLSafeTimedSerializer(settings.MAGIC_LINK_SECRET)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Payload data (should contain 'sub' with user_id)
        expires_delta: Optional expiration time

    Returns:
        JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify JWT token and return payload

    Args:
        token: JWT token string

    Returns:
        Payload dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def generate_magic_link_token(email: str) -> str:
    """
    Generate magic link token for email

    Args:
        email: User email

    Returns:
        Token string
    """
    return magic_link_serializer.dumps(email, salt='magic-link')


def verify_magic_link_token(token: str, max_age: int = None) -> Optional[str]:
    """
    Verify magic link token

    Args:
        token: Token string
        max_age: Max age in seconds (default: from settings)

    Returns:
        Email if valid, None otherwise
    """
    if max_age is None:
        max_age = settings.MAGIC_LINK_EXPIRATION_MINUTES * 60

    try:
        email = magic_link_serializer.loads(
            token,
            salt='magic-link',
            max_age=max_age
        )
        return email
    except (SignatureExpired, BadSignature):
        return None


def hash_password(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)
