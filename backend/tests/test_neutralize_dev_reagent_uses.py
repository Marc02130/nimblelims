"""Selection and void math for the dev reagent-use script.

The script is not run against the dev database. CI exercises the predicate
and the quantity restore on the test database only.
"""
from datetime import date, datetime
from decimal import Decimal

from models.flexible_experiment import LimsRun
from models.reagent import Reagent, ReagentLot, ReagentUse
from scripts.neutralize_dev_reagent_uses import (
    EXPECTED_ACTIVE_COUNT,
    TARGET_USED_ON,
    decide,
    neutralize_uses,
    select_active_uses,
)


def test_decide_refuses_any_count_other_than_four_or_zero():
    assert decide(0, False) == "noop"
    assert decide(0, True) == "noop"
    assert decide(EXPECTED_ACTIVE_COUNT, False) == "apply"
    assert decide(3, False) == "refuse"
    assert decide(5, False) == "refuse"
    assert decide(3, True) == "apply"


def test_selects_only_active_rows_on_the_target_date(db_session, test_admin_user):
    user_id = test_admin_user.id
    reagent = Reagent(
        name=f"Dev PBS {user_id.hex[:8]}",
        created_by=user_id,
        modified_by=user_id,
    )
    db_session.add(reagent)
    db_session.flush()
    run = LimsRun(name=f"dev-use-run-{user_id.hex[:8]}", created_by=user_id)
    db_session.add(run)
    db_session.flush()

    def lot(number, remaining):
        row = ReagentLot(
            reagent_id=reagent.id,
            lot_number=number,
            quantity_remaining=remaining,
            created_by=user_id,
            modified_by=user_id,
        )
        db_session.add(row)
        db_session.flush()
        return row

    def use(parent, used_on, quantity, active):
        row = ReagentUse(
            reagent_lot_id=parent.id,
            lims_run_id=run.id,
            lot_number=parent.lot_number,
            used_on=used_on,
            quantity_used=Decimal(quantity),
            active=active,
            created_at=datetime(2026, 10, 28, 12, 0),
            modified_at=datetime(2026, 10, 28, 12, 0),
            created_by=user_id,
            modified_by=user_id,
        )
        db_session.add(row)
        db_session.flush()
        return row

    tracked = lot("L-A", Decimal("10"))
    open_remaining = lot("L-B", Decimal("8"))
    untracked = lot("L-C", None)
    zero_lot = lot("L-D", Decimal("0"))
    targets = [
        use(tracked, TARGET_USED_ON, "5", True),
        use(open_remaining, TARGET_USED_ON, "1", True),
        use(untracked, TARGET_USED_ON, "3", True),
        use(zero_lot, TARGET_USED_ON, "0", True),
    ]
    other_day = use(tracked, date(2026, 10, 29), "9", True)
    already_void = use(tracked, TARGET_USED_ON, "4", False)
    db_session.commit()

    found = select_active_uses(db_session)
    assert [row.id for row in found] == sorted((row.id for row in targets), key=lambda value: value)
    assert len(found) == 4
    assert other_day.id not in {row.id for row in found}
    assert already_void.id not in {row.id for row in found}

    report = neutralize_uses(db_session, found)
    db_session.commit()
    assert len(report) == 4
    db_session.refresh(tracked)
    db_session.refresh(open_remaining)
    db_session.refresh(untracked)
    db_session.refresh(zero_lot)
    assert tracked.quantity_remaining == Decimal("15")
    assert open_remaining.quantity_remaining == Decimal("9")
    assert untracked.quantity_remaining is None
    assert zero_lot.quantity_remaining == Decimal("0")
    for row in targets:
        db_session.refresh(row)
        assert row.active is False
        assert row.quantity_used == Decimal("0")
    db_session.refresh(other_day)
    db_session.refresh(already_void)
    assert other_day.active is True
    assert other_day.quantity_used == Decimal("9")
    assert already_void.quantity_used == Decimal("4")
    assert select_active_uses(db_session) == []
    assert decide(0, False) == "noop"
