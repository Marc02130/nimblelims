"""Read and update the lab's IANA timezone."""

from pydantic import Field
from app.schemas._instants import APIModel as BaseModel


class LabTimezoneResponse(BaseModel):
    timezone: str


class LabTimezoneUpdate(BaseModel):
    timezone: str = Field(..., max_length=64)
