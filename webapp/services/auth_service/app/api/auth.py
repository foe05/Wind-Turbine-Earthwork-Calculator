"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.database import get_db
from app.models.user import User, MagicLink, Session as SessionModel
from app.schemas.auth import (
    MagicLinkRequest, MagicLinkResponse,
    TokenVerifyRequest, TokenVerifyResponse,
    UserResponse, LogoutRequest, LogoutResponse
)
from app.core.security import (
    generate_magic_link_token, verify_magic_link_token,
    create_access_token, verify_token
)
from app.core.email import send_magic_link_email
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/request-login", response_model=MagicLinkResponse)
async def request_magic_link(
    request: MagicLinkRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Request a magic link for passwordless login

    This will:
    1. Create user if doesn't exist
    2. Generate magic link token
    3. Send email with link
    """
    # Get or create user
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        user = User(email=request.email, created_at=datetime.utcnow())
        db.add(user)
        db.commit()
        db.refresh(user)

    # Generate token
    token = generate_magic_link_token(request.email)

    # Store magic link in database
    expires_at = datetime.utcnow() + timedelta(minutes=settings.MAGIC_LINK_EXPIRATION_MINUTES)

    magic_link = MagicLink(
        token=token,
        user_id=user.id,
        expires_at=expires_at,
        ip_address=req.client.host,
        user_agent=req.headers.get("User-Agent", "")
    )

    db.add(magic_link)
    db.commit()

    # Send email
    email_sent = await send_magic_link_email(request.email, token)

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please try again."
        )

    return MagicLinkResponse(
        email=request.email,
        message=f"Magic link sent to {request.email}"
    )


@router.get("/verify/{token}", response_model=TokenVerifyResponse)
async def verify_magic_link(
    token: str,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Verify magic link token and return JWT

    This will:
    1. Verify token is valid and not expired
    2. Mark magic link as used
    3. Generate JWT access token
    4. Create session record
    """
    # Verify token
    email = verify_magic_link_token(token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Check magic link in database
    magic_link = db.query(MagicLink).filter(MagicLink.token == token).first()

    if not magic_link:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    if magic_link.used:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token already used"
        )

    if magic_link.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )

    # Get user
    user = db.query(User).filter(User.id == magic_link.user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Mark magic link as used
    magic_link.used = True
    magic_link.used_at = datetime.utcnow()

    # Update last login
    user.last_login = datetime.utcnow()

    # Create JWT token
    expires_delta = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    expires_at = datetime.utcnow() + expires_delta

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=expires_delta
    )

    # Create session record
    session = SessionModel(
        user_id=user.id,
        jwt_token=access_token,
        expires_at=expires_at,
        ip_address=req.client.host,
        user_agent=req.headers.get("User-Agent", "")
    )

    db.add(session)
    db.commit()
    db.refresh(user)

    return TokenVerifyResponse(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
        user=UserResponse.from_orm(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user

    Requires Authorization header with Bearer token
    """
    # Get token from header
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )

    token = auth_header.split(" ")[1]

    # Verify token
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Get user
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return UserResponse.from_orm(user)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    logout_request: LogoutRequest,
    db: Session = Depends(get_db)
):
    """
    Logout user by invalidating session

    Note: This doesn't actually revoke the JWT (stateless),
    but removes session from database for tracking
    """
    # Find and delete session
    session = db.query(SessionModel).filter(
        SessionModel.jwt_token == logout_request.token
    ).first()

    if session:
        db.delete(session)
        db.commit()

    return LogoutResponse(message="Successfully logged out")


@router.get("/dev/magic-links/{email}")
async def get_magic_links_for_dev(
    email: str,
    db: Session = Depends(get_db)
):
    """
    🔧 DEVELOPMENT ONLY: Get magic links for an email without sending email

    This endpoint helps with local development when SMTP is not configured.
    Only available when DEBUG=True or SMTP is not configured.

    Usage:
    1. Request login via POST /auth/request-login with your email
    2. Call this endpoint: GET /auth/dev/magic-links/{email}
    3. Copy the magic link URL and open it in your browser
    """
    # Only allow in development mode or when SMTP is not configured
    if not settings.DEBUG and settings.SMTP_HOST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode"
        )

    # Get user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email: {email}"
        )

    # Get all unused, non-expired magic links for this user
    magic_links = db.query(MagicLink).filter(
        MagicLink.user_id == user.id,
        MagicLink.used == False,
        MagicLink.expires_at > datetime.utcnow()
    ).order_by(MagicLink.created_at.desc()).all()

    if not magic_links:
        return {
            "email": email,
            "message": "No active magic links found. Request a new login first.",
            "links": []
        }

    # Build full URLs
    links = []
    for ml in magic_links:
        magic_link_url = f"{settings.FRONTEND_URL}/login?token={ml.token}"
        links.append({
            "token": ml.token,
            "url": magic_link_url,
            "created_at": ml.created_at.isoformat(),
            "expires_at": ml.expires_at.isoformat(),
            "expires_in_minutes": int((ml.expires_at - datetime.utcnow()).total_seconds() / 60)
        })

    return {
        "email": email,
        "user_id": str(user.id),
        "message": "🔧 Development mode: Copy the URL below and open in your browser",
        "links": links
    }
