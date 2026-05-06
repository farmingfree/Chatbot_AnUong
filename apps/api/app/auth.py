"""
JWT Authentication middleware for NextAuth tokens
"""
import jwt
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security = HTTPBearer(auto_error=False)


def verify_jwt_token(token: str) -> dict:
    """
    Verify JWT token from NextAuth
    Returns decoded payload with user info
    """
    try:
        # Decode JWT with NEXTAUTH_SECRET
        payload = jwt.decode(
            token,
            settings.NEXTAUTH_SECRET,
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Dependency to get current user ID from JWT token
    Raises 401 if token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = verify_jwt_token(credentials.credentials)
    
    # Extract user_id from token payload
    # NextAuth typically stores user info in 'sub' or custom fields
    user_id = payload.get("sub") or payload.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    try:
        return UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID | None:
    """
    Dependency to get current user ID from JWT token
    Returns None if token is missing or invalid (does not raise exception)
    """
    if not credentials:
        return None
    
    try:
        payload = verify_jwt_token(credentials.credentials)
        user_id = payload.get("sub") or payload.get("user_id")
        
        if not user_id:
            return None
        
        return UUID(user_id)
    except (HTTPException, ValueError):
        return None
