"""Replay UI-created DDL after core Alembic (Brief OQ-11). Fail closed on collision."""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, text

from app.database import DATABASE_URL

logger = logging.getLogger(__name__)


def replay_ui_schema(url: str | None = None) -> None:
    engine = create_engine(url or DATABASE_URL)
    with engine.connect() as conn:
        exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='ui_schema_ddl_log'"
            )
        ).scalar()
        if not exists:
            logger.info("ui_schema_ddl_log missing — skip replay")
            return
        rows = conn.execute(
            text(
                "SELECT op, table_physical, column_physical, pg_type, nullable, list_fk "
                "FROM ui_schema_ddl_log ORDER BY seq"
            )
        ).mappings().all()
        for row in rows:
            op = row["op"]
            table = row["table_physical"]
            col = row["column_physical"]
            if op == "create_table":
                present = conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_name=:t"
                    ),
                    {"t": table},
                ).scalar()
                if present:
                    continue
                conn.execute(text("SELECT ui_schema_create_table(:t)"), {"t": table})
            elif op == "add_column":
                present = conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
                    ),
                    {"t": table, "c": col},
                ).scalar()
                if present:
                    continue
                conn.execute(
                    text("SELECT ui_schema_add_column(:t,:c,:ty,:n,:fk)"),
                    {
                        "t": table,
                        "c": col,
                        "ty": row["pg_type"],
                        "n": row["nullable"],
                        "fk": row["list_fk"],
                    },
                )
            elif op == "drop_column" and col:
                conn.execute(
                    text("SELECT ui_schema_drop_column(:t,:c)"),
                    {"t": table, "c": col},
                )
            elif op == "drop_table":
                conn.execute(text("SELECT ui_schema_drop_table(:t)"), {"t": table})
            else:
                logger.warning("Unknown ui_schema ddl op %s — fail closed", op)
                raise RuntimeError(f"unknown ui_schema ddl op {op}")
        conn.commit()
    engine.dispose()
    logger.info("ui_schema ddl log replayed (%s rows)", len(rows) if exists else 0)


if __name__ == "__main__":
    replay_ui_schema()
