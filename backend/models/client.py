from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import BaseModel, Base


class Client(BaseModel):
    __tablename__ = 'clients'
    
    # Client-specific fields
    billing_info = Column(JSONB, default={})
    
    # Relationships - explicitly specify foreign keys
    users = relationship("User", foreign_keys="User.client_id", back_populates="client")
    locations = relationship("Location", back_populates="client")
    projects = relationship("Project", back_populates="client")
    client_projects = relationship("ClientProject", back_populates="client")


class Location(BaseModel):
    __tablename__ = 'locations'
    
    # Location-specific fields
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    city = Column(String(255), nullable=False)
    state = Column(String(255), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(255), nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="locations")
    people = relationship("Person", secondary="people_locations", back_populates="locations")


class Person(BaseModel):
    __tablename__ = 'people'
    
    # Person-specific fields
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    title = Column(String(255))
    role = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'))
    
    # Relationships
    locations = relationship("Location", secondary="people_locations", back_populates="people")
    contact_methods = relationship("ContactMethod", back_populates="person")


class PeopleLocation(Base):
    __tablename__ = 'people_locations'
    
    person_id = Column(PostgresUUID(as_uuid=True), ForeignKey('people.id'), primary_key=True)
    location_id = Column(PostgresUUID(as_uuid=True), ForeignKey('locations.id'), primary_key=True)
    primary = Column(Boolean, default=False)
    notes = Column(String)


class ContactMethod(Base):
    __tablename__ = 'contact_methods'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(PostgresUUID(as_uuid=True), ForeignKey('people.id'), nullable=False)
    type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'), nullable=False)
    value = Column(String(255), nullable=False)
    description = Column(String)
    primary = Column(Boolean, default=False)
    verified = Column(Boolean, default=False)
    
    # Relationships
    person = relationship("Person", back_populates="contact_methods")


class ClientProject(BaseModel):
    __tablename__ = 'client_projects'
    
    # ClientProject-specific fields
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    custom_attributes = Column(JSONB, nullable=True, server_default='{}')
    
    # Relationships
    client = relationship("Client", back_populates="client_projects")
    projects = relationship("Project", back_populates="client_project")