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
    
    # Relationships - explicitly specify foreign keys
    role = relationship("Role", foreign_keys=[role_id], back_populates="users")
    client = relationship("Client", foreign_keys=[client_id], back_populates="users")
    projects = relationship(
        "Project", 
        secondary="project_users", 
        primaryjoin="User.id == project_users.c.user_id",
        secondaryjoin="Project.id == project_users.c.project_id",
        back_populates="users"
    )
    
    # Creator/modifier relationships (uncommented and fixed; add more if other models exist, e.g., for Analysis, Analyte, Unit)
    created_samples = relationship("Sample", foreign_keys="Sample.created_by", back_populates="creator")
    modified_samples = relationship("Sample", foreign_keys="Sample.modified_by", back_populates="modifier")
    created_results = relationship("Result", foreign_keys="Result.created_by", back_populates="creator")
    modified_results = relationship("Result", foreign_keys="Result.modified_by", back_populates="modifier")
    created_batches = relationship("Batch", foreign_keys="Batch.created_by", back_populates="creator")
    modified_batches = relationship("Batch", foreign_keys="Batch.modified_by", back_populates="modifier")
    created_analyses = relationship("Analysis", foreign_keys="Analysis.created_by", back_populates="creator")
    modified_analyses = relationship("Analysis", foreign_keys="Analysis.modified_by", back_populates="modifier")
    created_analytes = relationship("Analyte", foreign_keys="Analyte.created_by", back_populates="creator")
    modified_analytes = relationship("Analyte", foreign_keys="Analyte.modified_by", back_populates="modifier")
    created_units = relationship("Unit", foreign_keys="Unit.created_by", back_populates="creator")
    modified_units = relationship("Unit", foreign_keys="Unit.modified_by", back_populates="modifier")
    created_test_batteries = relationship("TestBattery", foreign_keys="TestBattery.created_by", back_populates="creator")
    modified_test_batteries = relationship("TestBattery", foreign_keys="TestBattery.modified_by", back_populates="modifier")
    entered_results = relationship("Result", foreign_keys="Result.entered_by", back_populates="entered_by_user")
    created_custom_attribute_configs = relationship("CustomAttributeConfig", foreign_keys="CustomAttributeConfig.created_by", back_populates="creator")
    modified_custom_attribute_configs = relationship("CustomAttributeConfig", foreign_keys="CustomAttributeConfig.modified_by", back_populates="modifier")


class Role(BaseModel):
    __tablename__ = 'roles'
    
    # Relationships - explicitly specify foreign keys
    users = relationship("User", foreign_keys="User.role_id", back_populates="role")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(BaseModel):
    __tablename__ = 'permissions'
    
    # Relationships - temporarily simplified
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

