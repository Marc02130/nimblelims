"""The lab clock. Lab managers and administrators read and update it."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.lab_time import INVALID_TIMEZONE, ensure_lab_setting, known_zone, resolve_lab_timezone
from app.core.rbac import require_lab_manager
from app.database import get_db
from app.schemas.lab_setting import LabTimezoneResponse, LabTimezoneUpdate
from models.user import User

router = APIRouter(prefix="/v1/lab-settings", tags=["lab-settings"])

_INVALID = (
    "That is not a known IANA time zone. Use a name such as America/New_York."
)


def _refuse_invalid() -> None:
    raise HTTPException(
        status_code=422,
        detail={"code": INVALID_TIMEZONE, "message": _INVALID},
    )


@router.get("", response_model=LabTimezoneResponse)
def read_lab_timezone(
    current_user: User = Depends(require_lab_manager),
    db: Session = Depends(get_db),
):
    """The zone the API uses for today's date. Seeds from LAB_TIMEZONE when empty."""
    return LabTimezoneResponse(timezone=resolve_lab_timezone(db))


@router.patch("", response_model=LabTimezoneResponse)
def update_lab_timezone(
    body: LabTimezoneUpdate,
    current_user: User = Depends(require_lab_manager),
    db: Session = Depends(get_db),
):
    """Save the lab zone. The environment does not override a saved value."""
    try:
        zone = known_zone(body.timezone)
    except ValueError:
        _refuse_invalid()
    name = getattr(zone, "key", None) or body.timezone.strip()
    row = ensure_lab_setting(db)
    row.timezone = name
    row.modified_by = current_user.id
    row.modified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return LabTimezoneResponse(timezone=row.timezone or name)
