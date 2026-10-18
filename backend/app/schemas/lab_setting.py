"""Read and update the lab's IANA timezone."""

from pydantic import BaseModel, Field


class LabTimezoneResponse(BaseModel):
    timezone: str


class LabTimezoneUpdate(BaseModel):
    timezone: str = Field(..., max_length=64)
