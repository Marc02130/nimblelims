#!/bin/bash
echo "=== FIXING MIGRATIONS ==="
echo ""
echo "1. Create alembic_version table if it doesn't exist:"
docker exec -it lims-db psql -U lims_user -d lims_db <<EOF
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
EOF

echo ""
echo "2. Check current migration version:"
docker exec -it lims-db psql -U lims_user -d lims_db -c "SELECT version_num FROM alembic_version;"

echo ""
echo "3. If empty, set to 0003 (before data migration):"
docker exec -it lims-db psql -U lims_user -d lims_db <<EOF
INSERT INTO alembic_version (version_num) VALUES ('0003')
ON CONFLICT (version_num) DO NOTHING;
EOF

echo ""
echo "4. Now run migrations to get to 0004 (creates admin user):"
docker exec lims-backend python run_migrations.py

echo ""
echo "5. Verify admin user exists:"
docker exec -it lims-db psql -U lims_user -d lims_db -c "SELECT username, email FROM users WHERE username = 'admin';"

