#!/usr/bin/env python3
"""
Create throwaway UAT users for security-high-s1-s6 live testing.

Does NOT reset existing admin passwords. Safe for dogfood stacks where
admin already completed must-change.

Users created (idempotent upsert by username):
  uat-admin     — Administrator, System client, must_change_password=true
  uat-labtech   — Lab Technician, System client, must_change_password=false
  uat-client-a  — Client role, Client A org (created if missing)
  uat-client-b  — Client role, Client B org (created if missing)

Temporary password (all): UatTemp1!xxxx
  - Meets complexity; uat-admin still has must_change=true for TC-S2-001

Usage:
  docker compose exec backend python create_uat_users.py
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from uuid import UUID

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Quiet noisy mapper overlap warnings for this one-shot script
warnings.filterwarnings("ignore", category=Warning, module="sqlalchemy")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models.user import User, Role
from models.client import Client
from app.core.security import get_password_hash

TEMP_PASSWORD = "UatTemp1!xxxx"
SYSTEM_CLIENT_ID = UUID("00000000-0000-0000-0000-000000000001")


def _owner_url() -> str:
    """
    Prefer owner/migrator URL so RLS does not hide clients/users when no
    app.current_user_id is set (runtime DATABASE_URL is lims_app).
    """
    return (
        os.getenv("MIGRATE_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://lims_user:lims_password@db:5432/lims_db"
    )


def _session():
    url = _owner_url()
    host = url.split("@")[-1] if "@" in url else url
    user = "unknown"
    if "://" in url and "@" in url:
        user = url.split("://", 1)[1].split(":", 1)[0]
    print(f"Connecting as DB user '{user}' → {host}")
    if user == "lims_app":
        print(
            "WARNING: connected as lims_app — RLS may hide clients. "
            "Set MIGRATE_DATABASE_URL to lims_user for this script."
        )
    engine = create_engine(url)
    return sessionmaker(bind=engine)(), engine


def _get_or_create_client(db, name: str, *, client_id: UUID | None = None) -> Client:
    c = db.query(Client).filter(Client.name == name).first()
    if c:
        return c
    kwargs = {
        "name": name,
        "description": f"UAT / system client ({name})",
        "active": True,
    }
    if client_id is not None:
        kwargs["id"] = client_id
    # billing_info required on some schemas
    try:
        c = Client(**kwargs, billing_info={})
    except TypeError:
        c = Client(**kwargs)
    db.add(c)
    db.flush()
    print(f"Created client: {name}")
    return c


def _upsert_user(
    db,
    *,
    username: str,
    email: str,
    name: str,
    role: Role,
    client: Client,
    must_change: bool,
) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.password_hash = get_password_hash(TEMP_PASSWORD)
        user.role_id = role.id
        user.client_id = client.id
        user.must_change_password = must_change
        user.active = True
        print(f"Updated existing user: {username}")
        return user
    user = User(
        name=name,
        username=username,
        email=email,
        password_hash=get_password_hash(TEMP_PASSWORD),
        role_id=role.id,
        client_id=client.id,
        active=True,
        must_change_password=must_change,
    )
    db.add(user)
    print(f"Created user: {username}")
    return user


def main() -> None:
    db, engine = _session()
    try:
        # Sanity: can we see anything at all?
        role_count = db.execute(text("SELECT count(*) FROM roles")).scalar()
        client_count = db.execute(text("SELECT count(*) FROM clients")).scalar()
        print(f"DB visible: roles={role_count}, clients={client_count}")

        admin_role = db.query(Role).filter(Role.name == "Administrator").first()
        tech_role = db.query(Role).filter(Role.name == "Lab Technician").first()
        client_role = db.query(Role).filter(Role.name == "Client").first()
        if not admin_role or not tech_role:
            print("ERROR: Required roles missing. Run migrations first.")
            sys.exit(1)
        if not client_role:
            print("WARNING: Client role missing — skipping uat-client-a/b")

        system = db.query(Client).filter(Client.name == "System").first()
        if not system:
            system = db.query(Client).filter(Client.id == SYSTEM_CLIENT_ID).first()
        if not system:
            system = _get_or_create_client(db, "System", client_id=SYSTEM_CLIENT_ID)

        _upsert_user(
            db,
            username="uat-admin",
            email="uat-admin@lims.example.com",
            name="UAT Administrator",
            role=admin_role,
            client=system,
            must_change=True,
        )
        _upsert_user(
            db,
            username="uat-labtech",
            email="uat-labtech@lims.example.com",
            name="UAT Lab Technician",
            role=tech_role,
            client=system,
            must_change=False,
        )

        if client_role:
            client_a = _get_or_create_client(db, "UAT Client A")
            client_b = _get_or_create_client(db, "UAT Client B")
            _upsert_user(
                db,
                username="uat-client-a",
                email="uat-client-a@lims.example.com",
                name="UAT Client A User",
                role=client_role,
                client=client_a,
                must_change=False,
            )
            _upsert_user(
                db,
                username="uat-client-b",
                email="uat-client-b@lims.example.com",
                name="UAT Client B User",
                role=client_role,
                client=client_b,
                must_change=False,
            )

        db.commit()
        print("=" * 56)
        print("UAT throwaway users ready")
        print("=" * 56)
        print(f"Password (all): {TEMP_PASSWORD}")
        print("  uat-admin     — must_change_password=true  (TC-S2-001)")
        print("  uat-labtech   — lab tech, System client   (S5/S6 live)")
        if client_role:
            print("  uat-client-a  — Client A               (TC-S1-002)")
            print("  uat-client-b  — Client B               (TC-S1-002)")
        print("=" * 56)
        print("Does not modify seed admin / lab-tech passwords.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
