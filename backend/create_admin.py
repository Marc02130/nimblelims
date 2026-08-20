#!/usr/bin/env python3
"""
Create admin user if it doesn't exist.

Production / bootstrap: set BOOTSTRAP_ADMIN_PASSWORD (must meet complexity).
Dev/demo: ALLOW_DEV_SEED_USERS=true may create admin with a temporary password
that requires change on first login.
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from models.user import User, Role, Client
from app.core.security import get_password_hash, validate_password_complexity
from app.core.config import ALLOW_DEV_SEED_USERS, ENVIRONMENT


def create_admin():
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()

        if admin_user:
            print("Admin user already exists!")
            print(f"  Username: {admin_user.username}")
            print(f"  Email: {admin_user.email}")
            print(f"  Active: {admin_user.active}")
            print(f"  must_change_password: {getattr(admin_user, 'must_change_password', None)}")
            return

        admin_role = db.query(Role).filter(Role.name == "Administrator").first()

        if not admin_role:
            print("ERROR: Administrator role not found!")
            print("Running migrations first...")
            try:
                from run_migrations import run_migrations
                run_migrations()
                admin_role = db.query(Role).filter(Role.name == "Administrator").first()
                if not admin_role:
                    print("ERROR: Administrator role still not found after migrations!")
                    sys.exit(1)
            except Exception as e:
                print(f"ERROR running migrations: {e}")
                print("Please run migrations manually:")
                print("  docker exec lims-backend python run_migrations.py")
                sys.exit(1)

        bootstrap_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "").strip()
        if bootstrap_password:
            errors = validate_password_complexity(
                bootstrap_password, username="admin", current_password=None
            )
            if errors:
                print("ERROR: BOOTSTRAP_ADMIN_PASSWORD fails complexity:")
                for err in errors:
                    print(f"  - {err}")
                sys.exit(1)
            password = bootstrap_password
        elif ALLOW_DEV_SEED_USERS:
            # Temporary weak password — must_change_password forces upgrade (Q7)
            password = "admin123"
            print("ALLOW_DEV_SEED_USERS: creating admin with temporary password (must change on login)")
        else:
            print("ERROR: No admin user and BOOTSTRAP_ADMIN_PASSWORD is not set.")
            print("For production: set BOOTSTRAP_ADMIN_PASSWORD to a complex secret.")
            print("For local/demo: set ALLOW_DEV_SEED_USERS=true")
            print(f"(ENVIRONMENT={ENVIRONMENT})")
            sys.exit(1)

        system_client = db.query(Client).filter(Client.name == "System").first()
        if not system_client:
            # Fallback well-known System client id from migrations
            from uuid import UUID
            system_client = db.query(Client).filter(
                Client.id == UUID("00000000-0000-0000-0000-000000000001")
            ).first()
        if not system_client:
            print("ERROR: System client not found. Run migrations.")
            sys.exit(1)

        admin_user = User(
            name="System Administrator",
            username="admin",
            email="admin@lims.example.com",
            password_hash=get_password_hash(password),
            role_id=admin_role.id,
            client_id=system_client.id,
            active=True,
            must_change_password=True,
        )

        db.add(admin_user)
        db.commit()

        print("=" * 50)
        print("ADMIN USER CREATED SUCCESSFULLY!")
        print("=" * 50)
        print("Username: admin")
        if bootstrap_password:
            print("Password: (from BOOTSTRAP_ADMIN_PASSWORD)")
        else:
            print("Password: admin123 (temporary — change on first login)")
        print("must_change_password: true")
        print("=" * 50)

    except Exception as e:
        print(f"ERROR creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
