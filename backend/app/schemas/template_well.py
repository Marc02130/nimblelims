from __future__ import annotations
import uuid
from typing import List, Optional
from pydantic import BaseModel


class TemplateWellDefinitionCreate(BaseModel):
    well_position:       str
    sample_role:         Optional[str] = None
    concentration_value: Optional[float] = None
    concentration_unit:  Optional[str] = None
    replicate_group:     Optional[str] = None


class TemplateWellDefinitionRead(BaseModel):
    id:                  uuid.UUID
    template_id:         uuid.UUID
    well_position:       str
    sample_role:         Optional[str] = None
    concentration_value: Optional[float] = None
    concentration_unit:  Optional[str] = None
    replicate_group:     Optional[str] = None

    class Config:
        from_attributes = True


class TemplateWellDefinitionListResponse(BaseModel):
    wells: List[TemplateWellDefinitionRead]
    total: int
