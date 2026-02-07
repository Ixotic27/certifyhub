"""
Authentication Dependencies
JWT token handling and user authentication
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config import settings
from app.database import database

# Security scheme
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode JWT access token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        User data from token
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    user_email = payload.get("email")
    user_type = payload.get("user_type")  # 'platform_admin' or 'club_admin'
    
    if user_email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return {
        "email": user_email,
        "user_type": user_type,
        "club_id": payload.get("club_id"),
        "user_id": payload.get("user_id")
    }


async def get_platform_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Require platform admin authentication
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Platform admin user data
        
    Raises:
        HTTPException: If user is not a platform admin
    """
    if current_user["user_type"] != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Platform admin access required."
        )
    
    return current_user


async def get_club_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Require club admin authentication
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Club admin user data
        
    Raises:
        HTTPException: If user is not a club admin
    """
    if current_user["user_type"] != "club_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Club admin access required."
        )
    
    return current_user