#!/usr/bin/env python3
"""Neutralize leftover dev reagent uses dated 2026-10-28. Not a migration.

The dev database has four test ``reagent_uses`` rows with ``used_on``
2026-10-28. This script selects only active rows on that date. It does not
match any other day, and it does not match a row that is already inactive.

Dry-run is the default and writes nothing. ``--apply`` follows the void
path in ``update_reagent_use``: add ``quantity_used`` back onto the lot when
``quantity_remaining`` is not null, then set ``quantity_used`` to 0 and
``active`` to false. Rows are not deleted.

Apply refuses to write when the active match count is not 4, unless
``--allow-count`` is passed. A count of 0 is a successful no-op, so a second
apply does nothing. ``--allow-count`` does not change that.

This command is not run in CI. The change that added it did not run it
against the dev database. Point ``DATABASE_URL`` at that database yourself.

Usage
-----
Export ``LIMS_APP_PASSWORD`` first. The shell expands it in the URL.

  export LIMS_APP_PASSWORD
  cd backend
  DATABASE_URL="postgresql://lims_app:${LIMS_APP_PASSWORD}@localhost:5432/lims_db" \\
    python scripts/neutralize_dev_reagent_uses.py
  DATABASE_URL="postgresql://lims_app:${LIMS_APP_PASSWORD}@localhost:5432/lims_db" \\
    python scripts/neutralize_dev_reagent_uses.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import models  # noqa: F401  (register mappers)
from models.reagent import ReagentLot, ReagentUse

TARGET_USED_ON = date(2026, 10, 28)
EXPECTED_ACTIVE_COUNT = 4


def decide(match_count: int, allow_other_count: bool) -> str:
    """``noop`` when nothing is left, ``apply`` when it is safe to write, else ``refuse``."""
    if match_count == 0:
        return "noop"
    if match_count == EXPECTED_ACTIVE_COUNT or allow_other_count is True:
        return "apply"
    return "refuse"


def select_active_uses(session: Session) -> list:
    """Active reagent uses dated 2026-10-28, ordered by id."""
    stmt = (
        select(ReagentUse)
        .where(
            ReagentUse.used_on == TARGET_USED_ON,
            ReagentUse.active.is_(True),
        )
        .order_by(ReagentUse.id)
    )
    return list(session.scalars(stmt).all())


def neutralize_uses(session: Session, rows: list) -> list:
    """Zero each use and mark it inactive. Return a report. Does not commit.

    The lot's ``quantity_remaining`` increases by the use's current quantity
    when that column is not null. A null remaining stays null.
    """
    report = []
    for row in rows:
        if row.active is not True:
            continue
        if row.used_on != TARGET_USED_ON:
            continue
        quantity = Decimal(row.quantity_used)
        lot = session.get(ReagentLot, row.reagent_lot_id)
        restored = None
        if lot is not None and lot.quantity_remaining is not None:
            lot.quantity_remaining = lot.quantity_remaining + quantity
            restored = lot.quantity_remaining
        row.quantity_used = Decimal("0")
        row.active = False
        report.append(
            {
                "id": str(row.id),
                "reagent_lot_id": str(row.reagent_lot_id),
                "quantity_returned": str(quantity),
                "quantity_remaining": None if restored is None else str(restored),
            }
        )
    return report


def _print_rows(rows: list) -> None:
    if len(rows) == 0:
        print("active reagent uses dated 2026-10-28: 0")
        return
    print(f"active reagent uses dated 2026-10-28: {len(rows)}")
    for row in rows:
        print(
            f"  id={row.id} lot={row.reagent_lot_id} "
            f"used_on={row.used_on} quantity_used={row.quantity_used} active={row.active}"
        )


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the changes. Omit this for a dry run.",
    )
    parser.add_argument(
        "--allow-count",
        action="store_true",
        help="Apply even when the active match count is not 4.",
    )
    args = parser.parse_args(argv)
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url == "":
        print("DATABASE_URL is required. This script does not pick a database.", file=sys.stderr)
        return 2
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            rows = select_active_uses(session)
            _print_rows(rows)
            action = decide(len(rows), args.allow_count)
            if args.apply is not True:
                print(f"dry-run: would {action}. No rows written.")
                return 0
            if action == "noop":
                print("apply: nothing to do.")
                return 0
            if action == "refuse":
                print(
                    f"refusing to write {len(rows)} rows. Expected {EXPECTED_ACTIVE_COUNT}. "
                    "Pass --allow-count to override.",
                    file=sys.stderr,
                )
                return 2
            report = neutralize_uses(session, rows)
            session.commit()
            print(f"apply: neutralized {len(report)} rows.")
            for item in report:
                print(
                    f"  id={item['id']} lot={item['reagent_lot_id']} "
                    f"returned={item['quantity_returned']} "
                    f"remaining={item['quantity_remaining']}"
                )
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
