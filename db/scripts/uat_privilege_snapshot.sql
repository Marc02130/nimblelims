-- UAT privilege snapshot for the database roles.
-- lims_app is the only runtime role. It must not be a superuser and must
-- not bypass row security. psql stops when the check raises.

SELECT rolname, rolsuper, rolbypassrls, rolcanlogin
  FROM pg_catalog.pg_roles
 WHERE rolname IN ('lims_app', 'lims_migrate', 'lims_user')  -- pragma: allowlist secret
 ORDER BY rolname;

DO $$
DECLARE
    app_super boolean;
    app_bypass boolean;
BEGIN
    SELECT rolsuper, rolbypassrls
      INTO app_super, app_bypass
      FROM pg_catalog.pg_roles
     WHERE rolname = 'lims_app';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'lims_app role is missing';
    END IF;
    IF app_super IS DISTINCT FROM false THEN
        RAISE EXCEPTION 'lims_app rolsuper must be false (got %)', app_super;
    END IF;
    IF app_bypass IS DISTINCT FROM false THEN
        RAISE EXCEPTION 'lims_app rolbypassrls must be false (got %)', app_bypass;
    END IF;
END $$;
