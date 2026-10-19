"""Read and update the lab's IANA timezone."""

from typing import Optional

from pydantic import Field
from app.schemas._instants import APIModel as BaseModel


class LabTimezoneResponse(BaseModel):
    timezone: Optional[str] = None
    timezone_configured: bool


class LabTimezoneUpdate(BaseModel):
    timezone: str = Field(..., max_length=64)
