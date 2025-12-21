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
        print("=" * 50, file=sys.stderr, flush=True)
        print("RUNNING DATABASE MIGRATIONS", file=sys.stderr, flush=True)
        print("=" * 50, file=sys.stderr, flush=True)
        print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'hidden'}", file=sys.stderr, flush=True)
        command.upgrade(alembic_cfg, "head")
        print("=" * 50, file=sys.stderr, flush=True)
        print("MIGRATIONS COMPLETED SUCCESSFULLY!", file=sys.stderr, flush=True)
        print("=" * 50, file=sys.stderr, flush=True)
        
    except Exception as e:
        print("=" * 50, file=sys.stderr, flush=True)
        print(f"MIGRATION FAILED: {e}", file=sys.stderr, flush=True)
        print("=" * 50, file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
