# How to Inspect Containers and Debug

## Access Containers

### Backend Container
```bash
# Get shell access
docker exec -it lims-backend bash

# Once inside, you can:
cd /app
ls -la
cat app/main.py
python -c "from app.database import SessionLocal; db = SessionLocal(); from models.user import User; print(db.query(User).count())"
```

### Database Container
```bash
# Get shell access
docker exec -it lims-db bash

# Access PostgreSQL
psql -U lims_user -d lims_db

# Inside psql:
\dt                    # List all tables
SELECT * FROM users;   # Check users
SELECT * FROM roles;    # Check roles
SELECT version_num FROM alembic_version;  # Check migration version
\q                     # Quit
```

### Frontend Container
```bash
# Get shell access
docker exec -it lims-frontend sh

# Check files
ls -la /usr/share/nginx/html
cat /usr/share/nginx/html/index.html
```

## Check Database State

### Quick Database Check
```bash
# Check if admin user exists
docker exec -it lims-db psql -U lims_user -d lims_db -c "SELECT username, email, active FROM users;"

# Check total user count
docker exec -it lims-db psql -U lims_user -d lims_db -c "SELECT COUNT(*) FROM users;"

# Check if roles exist
docker exec -it lims-db psql -U lims_user -d lims_db -c "SELECT name FROM roles;"

# Check migration version
docker exec -it lims-db psql -U lims_user -d lims_db -c "SELECT version_num FROM alembic_version;"

# Check all tables
docker exec -it lims-db psql -U lims_user -d lims_db -c "\dt"
```

## Check Backend Code

### View Files in Container
```bash
# List backend files
docker exec lims-backend ls -la /app

# Check if migrations directory exists
docker exec lims-backend ls -la /app/db/migrations/versions/

# View migration file
docker exec lims-backend cat /app/db/migrations/versions/0004_initial_data.py | grep -A 10 "admin"

# Check if run_migrations.py exists
docker exec lims-backend cat /app/run_migrations.py
```

## Run Migrations Manually

Migrations run automatically on backend startup, but you can run them manually if needed:

### Inside Backend Container
```bash
# Get shell
docker exec -it lims-backend bash

# Inside container:
cd /app
python run_migrations.py

# Check if it worked
python -c "from app.database import SessionLocal; from models.user import User; db = SessionLocal(); print('Users:', db.query(User).count())"
```

### From Host
```bash
# Run migrations directly
docker exec lims-backend python run_migrations.py

# Check migration version
docker exec lims-db psql -U lims_user -d lims_db -c "SELECT version_num FROM alembic_version;"
```

## Check Logs

### Backend Logs
```bash
# All logs
docker logs lims-backend

# Last 50 lines
docker logs lims-backend --tail 50

# Follow logs in real-time
docker logs -f lims-backend

# Logs with timestamps
docker logs lims-backend --timestamps
```

### Database Logs
```bash
docker logs lims-db --tail 50
```

### Frontend Logs
```bash
docker logs lims-frontend --tail 50
```

## Test Database Connection from Backend

```bash
# Test database connection
docker exec lims-backend python -c "
from app.database import SessionLocal, engine
from sqlalchemy import text
db = SessionLocal()
result = db.execute(text('SELECT COUNT(*) FROM users'))
print('User count:', result.scalar())
db.close()
"
```

## Check Environment Variables

```bash
# Backend env vars
docker exec lims-backend env | grep DATABASE

# Check DATABASE_URL
docker exec lims-backend printenv DATABASE_URL
```

## Run Python Code in Container

```bash
# Test database connection
docker exec lims-backend python -c "
from app.database import SessionLocal
from models.user import User
db = SessionLocal()
users = db.query(User).all()
print(f'Total users: {len(users)}')
for u in users:
    print(f'  - {u.username} ({u.email})')
db.close()
"
```

## Check Migration Status

```bash
# Check what migrations have run
docker exec -it lims-db psql -U lims_user -d lims_db -c "SELECT * FROM alembic_version;"

# Check if migration tables exist
docker exec -it lims-db psql -U lims_user -d lims_db -c "\dt" | grep alembic
```

## Force Re-run Migrations

**Warning:** This will delete all data!

```bash
# Remove all containers and volumes (fresh start)
docker-compose down -v

# Rebuild and start (migrations run automatically)
docker-compose up -d --build
```

Or manually reset:
```bash
# Drop and recreate (DANGER - deletes data)
docker exec -it lims-db psql -U lims_user -d lims_db -c "DROP TABLE IF EXISTS alembic_version CASCADE;"

# Then run migrations again
docker exec lims-backend python run_migrations.py
```

## Quick Debug Checklist

```bash
# 1. Check containers are running
docker ps | grep lims

# 2. Check database has tables
docker exec -it lims-db psql -U lims_user -d lims_db -c "\dt"

# 3. Check if users table exists and has data
docker exec -it lims-db psql -U lims_user -d lims_db -c "SELECT COUNT(*) FROM users;"

# 4. Check backend can connect to database
docker exec lims-backend python -c "from app.database import engine; print(engine.connect())"

# 5. Check migration version
docker exec -it lims-db psql -U lims_user -d lims_db -c "SELECT version_num FROM alembic_version;"

# 6. Check backend logs for errors
docker logs lims-backend --tail 100 | grep -i error
```

