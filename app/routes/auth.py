"""
Authentication Routes
Login, logout, password change endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.database import database
from app.auth import verify_password, hash_password, create_access_token, get_current_user

router = APIRouter()


# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    status: str
    message: str
    access_token: str
    user_type: str
    club_id: str = None
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Login endpoint for both Platform Admins and Club Admins
    
    Process:
    1. Check platform_admins table
    2. If not found, check club_administrators table
    3. Verify password
    4. Create JWT token
    5. Update last_login timestamp
    """
    
    # Try Platform Admin first
    platform_admin = await database.fetch_one(
        """
        SELECT id, email, password_hash, full_name, is_active, must_change_password
        FROM platform_admins
        WHERE email = :email
        """,
        {"email": credentials.email}
    )
    
    if platform_admin:
        # Platform Admin found
        if not platform_admin["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact support."
            )
        
        # Verify password
        if not verify_password(credentials.password, platform_admin["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        await database.execute(
            "UPDATE platform_admins SET last_login = NOW() WHERE id = :id",
            {"id": platform_admin["id"]}
        )
        
        # Create token
        token_data = {
            "email": platform_admin["email"],
            "user_type": "platform_admin",
            "user_id": str(platform_admin["id"])
        }
        access_token = create_access_token(token_data)
        
        return LoginResponse(
            status="success",
            message="Login successful",
            access_token=access_token,
            user_type="platform_admin",
            must_change_password=platform_admin["must_change_password"]
        )
    
    # Try Club Admin
    club_admin = await database.fetch_one(
        """
        SELECT id, club_id, email, password_hash, full_name, is_active, must_change_password
        FROM club_administrators
        WHERE email = :email
        """,
        {"email": credentials.email}
    )
    
    if club_admin:
        # Club Admin found
        if not club_admin["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact your club owner."
            )
        
        # Verify password
        if not verify_password(credentials.password, club_admin["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        await database.execute(
            "UPDATE club_administrators SET last_login = NOW() WHERE id = :id",
            {"id": club_admin["id"]}
        )
        
        # Create token
        token_data = {
            "email": club_admin["email"],
            "user_type": "club_admin",
            "user_id": str(club_admin["id"]),
            "club_id": str(club_admin["club_id"])
        }
        access_token = create_access_token(token_data)
        
        return LoginResponse(
            status="success",
            message="Login successful",
            access_token=access_token,
            user_type="club_admin",
            club_id=str(club_admin["club_id"]),
            must_change_password=club_admin["must_change_password"]
        )
    
    # Not found in either table
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password"
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Change password for current user
    """
    
    # Validate new password
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )
    
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Get user from database
    if current_user["user_type"] == "platform_admin":
        user = await database.fetch_one(
            "SELECT password_hash FROM platform_admins WHERE email = :email",
            {"email": current_user["email"]}
        )
        table = "platform_admins"
    else:
        user = await database.fetch_one(
            "SELECT password_hash FROM club_administrators WHERE email = :email",
            {"email": current_user["email"]}
        )
        table = "club_administrators"
    
    # Verify current password
    if not verify_password(request.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Hash new password
    new_password_hash = hash_password(request.new_password)
    
    # Update password
    await database.execute(
        f"""
        UPDATE {table}
        SET password_hash = :password_hash,
            password_changed_at = NOW(),
            must_change_password = FALSE
        WHERE email = :email
        """,
        {"password_hash": new_password_hash, "email": current_user["email"]}
    )
    
    return {
        "status": "success",
        "message": "Password changed successfully"
    }


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client should delete token)
    """
    return {
        "status": "success",
        "message": "Logged out successfully"
    }


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    return {
        "email": current_user["email"],
        "user_type": current_user["user_type"],
        "club_id": current_user.get("club_id")
    }