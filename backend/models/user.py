from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel

# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', PostgresUUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', PostgresUUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True)
)


class User(BaseModel):
    __tablename__ = 'users'
    
    # User-specific fields
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role_id = Column(PostgresUUID(as_uuid=True), ForeignKey('roles.id'), nullable=False)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey('clients.id'), nullable=True)
    last_login = Column(DateTime)
    
    # Relationships
    role = relationship("Role", back_populates="users")
    client = relationship("Client", back_populates="users")
    created_samples = relationship("Sample", foreign_keys="Sample.created_by", back_populates="creator")
    modified_samples = relationship("Sample", foreign_keys="Sample.modified_by", back_populates="modifier")


class Role(BaseModel):
    __tablename__ = 'roles'
    
    # Relationships
    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(BaseModel):
    __tablename__ = 'permissions'
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
