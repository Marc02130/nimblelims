from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class User(Base):
    __tablename__ = 'users'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
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


class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")


class Permission(Base):
    __tablename__ = 'permissions'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")


class RolePermission(Base):
    __tablename__ = 'role_permissions'
    
    role_id = Column(PostgresUUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(PostgresUUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True)
