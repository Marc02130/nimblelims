# Clients RLS Issue Analysis

## Problem
Client users can see ALL clients in the clients list, when they should only see their own client record.

## What Works
- ✅ `client_projects` RLS works correctly - client users only see their own client's projects
- ✅ `projects` RLS works correctly - client users only see their own client's projects
- ❌ `clients` RLS does NOT work - client users see all clients

## Key Differences

### Table Structure
- **clients**: Top-level entity (id = client identifier)
- **client_projects**: Belongs to a client (client_id references clients.id)
- **projects**: Belongs to a client and optionally a client_project

### RLS Configuration
- **client_projects**: 
  - RLS enabled: ✅
  - FORCE RLS: ❌ (relforcerowsecurity = f)
  - Policy works: ✅
  
- **clients**:
  - RLS enabled: ✅
  - FORCE RLS: ✅ (relforcerowsecurity = t) - REQUIRED because app runs as table owner
  - Policy works: ❌

### Policy Comparison

**client_projects_access (WORKING):**
```sql
CREATE POLICY client_projects_access ON client_projects
FOR ALL
USING (
    is_admin() 
    OR EXISTS (
        SELECT 1 FROM users u
        WHERE u.id = current_user_id()
        AND u.client_id = client_projects.client_id
    )
    OR EXISTS (
        SELECT 1 FROM users u
        WHERE u.id = current_user_id()
        AND u.client_id = '00000000-0000-0000-0000-000000000001'::UUID
        AND client_projects.active = true
    )
);
```

**clients_access (NOT WORKING):**
```sql
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

The policies are structurally identical, but clients RLS doesn't work.

## Possible Causes

1. **FORCE RLS Interaction**: When FORCE RLS is enabled, PostgreSQL might evaluate policies differently
2. **Table Owner Context**: Even with FORCE RLS, there might be edge cases with SECURITY DEFINER functions
3. **Policy Evaluation Order**: The EXISTS clauses might be evaluated in a way that bypasses RLS for the table owner
4. **Connection Pooling**: Session variables might not persist correctly (but this would affect other tables too)

## Attempted Fixes

1. ✅ Migration 0031: Initial RLS policy
2. ✅ Migration 0032: More explicit policy with additional checks
3. ✅ Migration 0033: Simplified policy matching client_projects pattern
4. ✅ Migration 0034: Added FORCE RLS and recreated policy

All migrations applied successfully, but RLS still doesn't filter clients for client users.

## Next Steps

1. Test if removing FORCE RLS helps (but this would allow table owner to bypass RLS)
2. Try a RESTRICTIVE policy instead of PERMISSIVE
3. Check if there's a PostgreSQL bug or version-specific issue
4. Consider application-level filtering as a workaround (not ideal, but might be necessary)
