# URGENT FIX: Apply RLS Policy to Clients Table

## Problem
Client role users can see ALL clients in the client list. They should ONLY see their own client record.

## Solution
The migration `0031_add_clients_rls.py` has been created but hasn't been run yet. You need to apply it.

## Option 1: Run the Migration (Recommended)

If you're using Docker:
```bash
docker-compose exec backend python run_migrations.py
```

Or if running locally:
```bash
cd backend
python run_migrations.py
```

## Option 2: Apply SQL Directly (Immediate Fix)

If you have direct database access, run this SQL:

```sql
-- Enable RLS on clients table
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS clients_access ON clients;

-- Create clients_access policy
CREATE POLICY clients_access ON clients
FOR ALL
USING (
    is_admin() 
    OR EXISTS (
        SELECT 1 FROM users u
        WHERE u.id = current_user_id()
        AND u.client_id = '00000000-0000-0000-0000-000000000001'::UUID
    )
    OR EXISTS (
        SELECT 1 FROM users u
        WHERE u.id = current_user_id()
        AND u.client_id = clients.id
    )
);
```

You can also use the SQL file:
```bash
psql -U lims_user -d lims_db -f backend/fix_clients_rls.sql
```

## What This Does

The RLS policy ensures:
- **Administrators**: See all clients
- **System client users** (lab employees): See all clients
- **Regular client users**: See ONLY their own client record (where `clients.id = user.client_id`)

## Verification

After applying, test by:
1. Logging in as a client user
2. Navigating to the clients list
3. You should see ONLY one client record (their own)
