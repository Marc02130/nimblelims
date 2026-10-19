"""
Database configuration and session management
"""
from __future__ import annotations

from typing import Optional
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from app.core.db_url import resolve_db_url
from models import Base

load_dotenv()

# Runtime URL is lims_app. Migrations call resolve_db_url(migrate=True).
DATABASE_URL = resolve_db_url()



def _ms(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _engine_kwargs(url: str) -> dict:
    """Bound every wait so one stuck request can't wedge the pool (UAT RT-7).

    Server-side: timezone UTC, lock_timeout, statement_timeout and
    idle_in_transaction_session_timeout (ms; 0 disables). Client-side:
    pool_timeout (s) so a request waiting for a connection fails instead of
    hanging forever; pool_pre_ping drops connections the server closed.
    timezone=UTC keeps a lab-day write of an aware UTC datetime on a
    ``timestamp without time zone`` column from shifting to the server zone.
    """
    kwargs: dict = {"pool_pre_ping": True, "pool_timeout": _ms("DB_POOL_TIMEOUT_S", 10)}
    if url.startswith("postgresql"):
        opts = "-c timezone=UTC " + " ".join(
            f"-c {guc}={_ms(env, default)}"
            for guc, env, default in (
                ("lock_timeout", "DB_LOCK_TIMEOUT_MS", 5000),
                ("statement_timeout", "DB_STATEMENT_TIMEOUT_MS", 60000),
                ("idle_in_transaction_session_timeout", "DB_IDLE_TX_TIMEOUT_MS", 60000),
            )
        )
        kwargs["connect_args"] = {"options": opts}
    return kwargs


engine = create_engine(DATABASE_URL, **_engine_kwargs(DATABASE_URL))
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


def release_transaction(db: Session, *, keep_loaded: bool = False) -> None:
    """End the open transaction and hand the connection back to the pool before
    an outside call (model, R, SMTP) or a background task.

    idle_in_transaction_session_timeout (60 s) kills a connection left idle in
    a transaction (UAT 67481e9, e47c53f). The session opens a fresh
    transaction on next use; the after_begin hook re-applies the RLS GUCs.
    keep_loaded=True keeps already-loaded objects usable without reloading.
    """
    if not keep_loaded:
        db.commit()
        return
    previous = db.expire_on_commit
    db.expire_on_commit = False
    try:
        db.commit()
    finally:
        db.expire_on_commit = previous


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


class MissingRlsContext(RuntimeError):
    """A background session was asked for without the originating user."""


@contextmanager
def background_session(user_id, client_id=None, session_factory=None) -> Iterator[Session]:
    """A session for work outside the request (background task, thread) that
    carries the originating request's RLS context (user and client).

    Capture user_id/client_id at request time and pass them in. Without a user
    this fails closed: under RLS a contextless session sees no client rows, so
    work would silently do nothing, or worse, run unscoped as a superuser.
    The after_begin hook re-applies the context after every commit.
    """
    if not user_id:
        raise MissingRlsContext("background session needs the originating user_id")
    db = (session_factory or SessionLocal)()
    try:
        set_rls_context(db, user_id=str(user_id), client_id=str(client_id) if client_id else None)
        yield db
    finally:
        db.info.pop("rls_user_id", None)
        db.info.pop("rls_client_id", None)
        db.close()


def get_db():
    """Dependency to get database session"""
    from app.core.lab_time import publish_lab_zone

    db = SessionLocal()
    try:
        # Before body validation, so date validators see the lab zone.
        # A corrupt saved zone is remembered and does not block this session.
        publish_lab_zone(db)
        yield db
    finally:
        db.info.pop("rls_user_id", None)
        db.info.pop("rls_client_id", None)
        db.close()
