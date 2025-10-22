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
    set_current_user_id
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
    # Find user by username
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.active:
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
    
    return LoginResponse(
        access_token=access_token,
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.name,
        permissions=permissions
    )

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
