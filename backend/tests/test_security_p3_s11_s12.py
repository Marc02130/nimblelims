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
        """Overlay must use !reset — plain ports: [] does not unset base 5432."""
        import subprocess

        root = Path(__file__).resolve().parents[2]
        prod = (root / "docker-compose.prod.yml").read_text()
        assert "!reset" in prod
        assert "ENVIRONMENT: production" in prod
        assert "ALLOW_INSECURE_DEFAULTS" in prod
        assert "POSTGRES_PASSWORD" in prod

        # Live merge check (Compose v2+); skip if docker unavailable
        import os

        try:
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(root / "docker-compose.yml"),
                    "-f",
                    str(root / "docker-compose.prod.yml"),
                    "config",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(root),
                env={
                    **os.environ,
                    "POSTGRES_PASSWORD": "test-only",
                    "SECRET_KEY": "test-only-secret-key-not-prod",
                    "LIMS_APP_PASSWORD": "test-only",
                },
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("docker compose not available")
        if result.returncode != 0:
            pytest.skip(f"compose config failed: {result.stderr[:200]}")

        # Extract db service block; must not publish host 5432
        in_db = False
        db_lines = []
        for line in result.stdout.splitlines():
            if line.startswith("  db:"):
                in_db = True
                db_lines.append(line)
                continue
            if in_db:
                if (
                    line.startswith("  ")
                    and not line.startswith("    ")
                    and line.strip().endswith(":")
                ):
                    break
                db_lines.append(line)
        db_text = "\n".join(db_lines)
        assert "5432" not in db_text, f"prod merge still mentions 5432 under db:\n{db_text}"
