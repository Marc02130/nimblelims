"""
Authentication router for LIMS MVP
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, VerifyEmailRequest, VerifyEmailResponse
from app.core.security import (
    verify_password, 
    create_access_token, 
    get_user_permissions,
    set_current_user_id,
    get_current_user
)
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token with permissions
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Check total user count first
    user_count = db.query(User).count()
    if user_count == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No users found in database. Run: docker exec lims-backend python run_migrations.py",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user:
        logger.warning(f"User not found: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    password_valid = verify_password(login_data.password, user.password_hash)
    
    if not password_valid:
        logger.warning(f"Password verification failed for user: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.active:
        logger.warning(f"Inactive user attempted login: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    # Get user permissions
    permissions = get_user_permissions(user, db)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.name,
            "permissions": permissions
        },
        expires_delta=access_token_expires
    )
    
    # Update last login
    from sqlalchemy import func
    user.last_login = func.now()
    db.commit()
    
    # Set current user for RLS
    set_current_user_id(str(user.id), db)
    
    response = LoginResponse(
        access_token=access_token,
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.name,
        permissions=permissions
    )
    
    return response

@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information
    """
    permissions = get_user_permissions(current_user, db)
    
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.name,
        "permissions": permissions,
        "client_id": str(current_user.client_id) if current_user.client_id else None,
    }

@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    verify_data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Verify user email address (stub implementation)
    """
    # Find user by email
    user = db.query(User).filter(User.email == verify_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # TODO: Implement actual email verification logic
    # For now, just return success
    return VerifyEmailResponse(
        message="Email verification successful",
        verified=True
    )
