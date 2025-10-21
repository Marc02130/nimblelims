from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base


class Client(Base):
    __tablename__ = 'clients'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Client-specific fields
    billing_info = Column(JSONB, default={})
    
    # Relationships
    users = relationship("User", back_populates="client")
    projects = relationship("Project", back_populates="client")
    locations = relationship("Location", back_populates="client")


class Location(Base):
    __tablename__ = 'locations'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
    # Location-specific fields
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    city = Column(String(255), nullable=False)
    state = Column(String(255), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(255), default='US')
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    type = Column(PostgresUUID(as_uuid=True), ForeignKey('list_entries.id'))
    
    # Relationships
    client = relationship("Client", back_populates="locations")
    people = relationship("Person", secondary="people_locations", back_populates="locations")


class Person(Base):
    __tablename__ = 'people'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id'))
    
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
