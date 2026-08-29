"""P2 schemas: routing map, work orders, step accepted sample types, Route."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class StepAcceptedSampleTypesPut(BaseModel):
    sample_type_ids: List[UUID] = Field(default_factory=list)


class StepAcceptedSampleTypesResponse(BaseModel):
    step_id: UUID
    sample_type_ids: List[UUID]
    count: int


class RoutingMapCreate(BaseModel):
    analysis_id: UUID
    sample_type_id: Optional[UUID] = Field(
        None,
        description="Ignored. Sample types are taken from the first process's first experiment/LIMS Run.",
    )
    tat_min: int = Field(..., ge=1)
    tat_max: int = Field(..., ge=1)
    process_definition_ids: List[UUID] = Field(..., min_length=1)
    active: bool = True

    @model_validator(mode="after")
    def range_ok(self):
        if self.tat_max < self.tat_min:
            raise ValueError("tat_max must be >= tat_min")
        return self


class RoutingMapUpdate(BaseModel):
    tat_min: Optional[int] = Field(None, ge=1)
    tat_max: Optional[int] = Field(None, ge=1)
    process_definition_ids: Optional[List[UUID]] = Field(None, min_length=1)
    active: Optional[bool] = None


class RoutingMapRead(BaseModel):
    id: UUID
    analysis_id: UUID
    sample_type_id: UUID
    tat_min: int
    tat_max: int
    process_definition_ids: List[UUID]
    active: bool
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class WorkOrderRead(BaseModel):
    id: UUID
    asked_for_id: UUID
    sample_id: UUID
    sample_name: Optional[str] = None
    analysis_id: UUID
    analysis_name: Optional[str] = None
    process_definition_ids: List[UUID]
    status: str
    process_id: Optional[UUID] = None
    latest_process_id: Optional[UUID] = None
    started_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class WorkOrderListResponse(BaseModel):
    items: List[WorkOrderRead]
    count: int


class RouteRequest(BaseModel):
    asked_for_ids: List[UUID] = Field(default_factory=list)


class RouteItem(BaseModel):
    asked_for_id: UUID
    work_order: Optional[WorkOrderRead] = None
    no_route: bool = False


class RouteResponse(BaseModel):
    items: List[RouteItem]
    count: int
