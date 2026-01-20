# LIMS Admin Setup Guide

## Initial Admin Credentials

After starting the application with `docker-compose up -d --build`, Alembic migrations automatically create an initial admin user with the following credentials:

- **Username**: `admin`
- **Password**: `admin123`
- **Email**: `admin@lims.example.com`

## ⚠️ SECURITY WARNING

**You MUST change the default admin password immediately after first login!**

The default password is only for initial setup and should never be used in production.

## How to Change Admin Password

### Option 1: Through the Web Interface
1. Login to the LIMS at http://localhost:3000
2. Navigate to User Management (when implemented)
3. Change the admin user's password

### Option 2: Through Database (Direct)
```sql
-- Connect to the database
psql -h localhost -U lims_user -d lims_db

-- Update the admin password (replace 'new_secure_password' with your desired password)
UPDATE users 
SET password_hash = crypt('new_secure_password', gen_salt('bf', 12))
WHERE username = 'admin';
```

### Option 3: Using Python Script
```python
# Run this in the backend directory
from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models.user import User

db = SessionLocal()
admin_user = db.query(User).filter(User.username == "admin").first()
admin_user.password_hash = get_password_hash("your_new_password")
db.commit()
db.close()
```

## Creating Additional Admin Users

### Through Database
```sql
-- Create a new admin user
INSERT INTO users (name, username, email, password_hash, role_id, client_id, active, created_at, modified_at) 
VALUES (
    'New Admin Name',
    'newadmin',
    'newadmin@yourcompany.com',
    crypt('secure_password', gen_salt('bf', 12)),
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',  -- Administrator role ID
    '00000000-0000-0000-0000-000000000001',  -- System client ID
    true,
    NOW(),
    NOW()
);
```

## Security Best Practices

1. **Change Default Password**: Always change the default admin password
2. **Strong Passwords**: Use complex passwords with mixed case, numbers, and symbols
3. **Regular Updates**: Change passwords regularly
4. **Limit Admin Access**: Only create admin users for people who need full system access
5. **Monitor Access**: Keep track of who has admin access
6. **Use Environment Variables**: Store sensitive configuration in environment variables, not code

## Role-Based Access

The LIMS system includes the following roles:

- **Administrator**: Full system access (all permissions)
- **Lab Manager**: Laboratory management permissions
- **Lab Technician**: Sample and test management permissions  
- **Client**: Read-only access to their project data

## Troubleshooting

### Cannot Login
1. Verify containers are running: `docker-compose ps`
2. Check backend logs for migration errors: `docker logs lims-backend | grep -i migration`
3. Verify migrations completed: `docker exec lims-db psql -U lims_user -d lims_db -c "SELECT version_num FROM alembic_version;"`
4. Check if the admin user exists: `docker exec lims-db psql -U lims_user -d lims_db -c "SELECT username, email FROM users WHERE username = 'admin';"`
5. If admin user is missing, run migrations manually: `docker exec lims-backend python run_migrations.py`

### Database Connection Issues
1. Check database credentials in environment variables
2. Ensure PostgreSQL is running and accessible
3. Verify network connectivity between services

## Support

For additional help with admin setup, refer to:
- Backend authentication: `.docs/backend-auth.md`
- Container inspection: `.docs/inspect_containers.md`
- API documentation: http://localhost:8000/docs
