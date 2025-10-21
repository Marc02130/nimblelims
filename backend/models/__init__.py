from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

# Import all models
from .user import User, Role, Permission, RolePermission
from .client import Client, Location, Person, PeopleLocation, ContactMethod
from .project import Project, ProjectUser
from .sample import Sample
from .container import Container, ContainerType, Contents
from .analysis import Analysis, Analyte, AnalysisAnalyte
from .test import Test
from .result import Result
from .batch import Batch, BatchContainer
from .list import List, ListEntry
from .unit import Unit

def get_engine():
    """Get database engine from environment variables."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://lims_user:lims_password@localhost:5432/lims_db"
    )
    return create_engine(database_url)

def get_session():
    """Get database session."""
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
