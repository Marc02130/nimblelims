#!/usr/bin/env python3
"""
Script to run Alembic migrations for LIMS MVP database.
"""
import os
import sys
from pathlib import Path
from alembic.config import Config
from alembic import command

def run_migrations():
    """Run database migrations."""
    # Get the backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Set up Alembic configuration
    alembic_cfg = Config("alembic.ini")
    
    # Set database URL from environment or use default
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://lims_user:lims_password@localhost:5432/lims_db"
    )
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    try:
        # Run migrations
        print("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
