#!/usr/bin/env python3
"""
Create admin user if it doesn't exist
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from models.user import User, Role
from app.core.security import get_password_hash

def create_admin():
    db = SessionLocal()
    try:
        # Check if admin user exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if admin_user:
            print("Admin user already exists!")
            print(f"  Username: {admin_user.username}")
            print(f"  Email: {admin_user.email}")
            print(f"  Active: {admin_user.active}")
            return
        
        # Get Administrator role
        admin_role = db.query(Role).filter(Role.name == "Administrator").first()
        
        if not admin_role:
            print("ERROR: Administrator role not found!")
            print("Running migrations first...")
            # Try to run migrations
            try:
                from run_migrations import run_migrations
                run_migrations()
                # Try again to get the role
                admin_role = db.query(Role).filter(Role.name == "Administrator").first()
                if not admin_role:
                    print("ERROR: Administrator role still not found after migrations!")
                    print("Please check database connection and migrations.")
                    sys.exit(1)
            except Exception as e:
                print(f"ERROR running migrations: {e}")
                print("Please run migrations manually:")
                print("  docker exec lims-backend python run_migrations.py")
                sys.exit(1)
        
        # Create admin user
        admin_user = User(
            name="System Administrator",
            username="admin",
            email="admin@lims.example.com",
            password_hash=get_password_hash("admin123"),
            role_id=admin_role.id,
            active=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print("=" * 50)
        print("ADMIN USER CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"Username: admin")
        print(f"Password: admin123")
        print(f"Email: admin@lims.example.com")
        print("=" * 50)
        print("⚠️  CHANGE THE PASSWORD IMMEDIATELY!")
        print("=" * 50)
        
    except Exception as e:
        print(f"ERROR creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()

