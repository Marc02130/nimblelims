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
  docker compose exec lims-backend python create_uat_users.py
  # or locally with DATABASE_URL / MIGRATE_DATABASE_URL set
"""
from __future__ import annotations

import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from models.user import User, Role
from models.client import Client
from app.core.security import get_password_hash

TEMP_PASSWORD = "UatTemp1!xxxx"


def _get_or_create_client(db, name: str) -> Client:
    c = db.query(Client).filter(Client.name == name).first()
    if c:
        return c
    c = Client(name=name, description=f"UAT throwaway org ({name})", active=True)
    db.add(c)
    db.flush()
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
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "Administrator").first()
        tech_role = db.query(Role).filter(Role.name == "Lab Technician").first()
        client_role = db.query(Role).filter(Role.name == "Client").first()
        if not admin_role or not tech_role:
            print("ERROR: Required roles missing. Run migrations first.")
            sys.exit(1)
        if not client_role:
            print("WARNING: Client role missing — skipping uat-client-a/b")

        system = (
            db.query(Client).filter(Client.name == "System").first()
            or db.query(Client).first()
        )
        if not system:
            print("ERROR: No clients found. Run migrations/seeds first.")
            sys.exit(1)

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


if __name__ == "__main__":
    main()
