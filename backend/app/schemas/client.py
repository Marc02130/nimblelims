"""
Pydantic schemas for clients
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ClientResponse(BaseModel):
    """Schema for client response"""
    id: UUID
    name: str
    description: Optional[str] = None
    billing_info: Optional[Dict[str, Any]] = None
    active: bool
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class ClientCreate(BaseModel):
    """Schema for creating a client"""
    name: str
    description: Optional[str] = None
    billing_info: Optional[Dict[str, Any]] = None


class ClientUpdate(BaseModel):
    """Schema for updating a client"""
    name: Optional[str] = None
    description: Optional[str] = None
    billing_info: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None

