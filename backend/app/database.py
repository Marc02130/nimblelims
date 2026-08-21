"""
Database configuration and session management
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from models import Base

load_dotenv()

# Runtime app URL — should be lims_app after P0d (owner URL is MIGRATE_DATABASE_URL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://lims_user:lims_password@localhost:5432/lims_db",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(SessionLocal, "after_begin")
def _apply_rls_gucs_on_begin(session, transaction, connection):
    """Re-apply transaction-local RLS GUCs after each BEGIN/COMMIT boundary (P0d)."""
    uid = session.info.get("rls_user_id")
    if uid:
        connection.execute(
            text("SELECT set_config('app.current_user_id', :v, true)"),
            {"v": str(uid)},
        )
    cid = session.info.get("rls_client_id")
    if cid:
        connection.execute(
            text("SELECT set_config('app.client_id', :v, true)"),
            {"v": str(cid)},
        )


def set_rls_context(
    db: Session,
    *,
    user_id: str,
    client_id: Optional[str] = None,
) -> None:
    """Bind RLS session variables for the current request/session (P0d)."""
    db.info["rls_user_id"] = str(user_id)
    if client_id:
        db.info["rls_client_id"] = str(client_id)
    else:
        db.info.pop("rls_client_id", None)

    db.execute(
        text("SELECT set_config('app.current_user_id', :v, true)"),
        {"v": str(user_id)},
    )
    if client_id:
        db.execute(
            text("SELECT set_config('app.client_id', :v, true)"),
            {"v": str(client_id)},
        )
    db.flush()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.info.pop("rls_user_id", None)
        db.info.pop("rls_client_id", None)
        db.close()
