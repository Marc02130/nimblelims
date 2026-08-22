"""P3: FORCE RLS / contents policy / prod compose overlay presence."""
from pathlib import Path

import pytest
from sqlalchemy import text


class TestS11ForceRls:
    def test_tenant_tables_force_rls(self, migrated_engine):
        tables = (
            "samples",
            "tests",
            "results",
            "projects",
            "batches",
            "containers",
            "client_projects",
            "contents",
        )
        with migrated_engine.connect() as conn:
            for name in tables:
                row = conn.execute(
                    text(
                        """
                        SELECT relrowsecurity, relforcerowsecurity
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public' AND c.relname = :t
                        """
                    ),
                    {"t": name},
                ).one()
                assert row[0] is True, f"{name} should have RLS enabled"
                assert row[1] is True, f"{name} should have FORCE RLS"

    def test_contents_policy_exists(self, migrated_engine):
        with migrated_engine.connect() as conn:
            n = conn.execute(
                text(
                    """
                    SELECT count(*) FROM pg_policy
                    WHERE polrelid = 'contents'::regclass
                    """
                )
            ).scalar()
            assert n >= 1

    def test_containers_insert_policy_separate(self, migrated_engine):
        with migrated_engine.connect() as conn:
            names = {
                r[0]
                for r in conn.execute(
                    text(
                        """
                        SELECT polname FROM pg_policy
                        WHERE polrelid = 'containers'::regclass
                        """
                    )
                )
            }
            assert "containers_insert" in names
            assert "containers_select" in names


class TestS12ProdCompose:
    def test_prod_overlay_clears_db_ports(self):
        root = Path(__file__).resolve().parents[2]
        prod = (root / "docker-compose.prod.yml").read_text()
        assert "ports: []" in prod or "ports:[]" in prod.replace(" ", "")
        assert "ENVIRONMENT: production" in prod or 'ENVIRONMENT: production' in prod
        assert "ALLOW_INSECURE_DEFAULTS" in prod
        assert "POSTGRES_PASSWORD" in prod
