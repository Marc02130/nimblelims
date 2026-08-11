"""Schemas for ELN aliquot/pool plan + execute (P0, all methods)."""
from enum import Enum
from typing import Optional, List, Any, Dict
from uuid import UUID
from pydantic import BaseModel, Field


class AliquotMethod(str, Enum):
    """Full v1 method matrix (Lab Ops L9 / Arch A6)."""
    by_mass = "by_mass"
    by_volume = "by_volume"  # inbound volume + conc → store mass
    by_count = "by_count"
    target_mass = "target_mass"
    target_volume = "target_volume"  # target vol + source conc → mass
    target_concentration = "target_concentration"
    target_count = "target_count"


# Columns / inputs expected per method (for UI)
METHOD_PROFILES: Dict[str, Dict[str, Any]] = {
    AliquotMethod.by_mass.value: {
        "label": "By mass",
        "required_inputs": ["amount", "amount_unit_id"],
        "optional_inputs": ["concentration", "concentration_unit_id"],
        "stores": ["amount", "concentration"],
        "description": "Transfer mass from source; optional copy concentration to dest",
    },
    AliquotMethod.by_volume.value: {
        "label": "By volume",
        "required_inputs": ["volume", "concentration", "concentration_unit_id"],
        "optional_inputs": ["volume_unit_id", "amount_unit_id"],
        "stores": ["amount", "concentration"],
        "description": "Inbound volume + concentration → mass; volume not stored",
    },
    AliquotMethod.by_count.value: {
        "label": "By count",
        "required_inputs": ["amount", "amount_unit_id"],
        "optional_inputs": [],
        "stores": ["amount"],
        "description": "Transfer count (cells, colonies, etc.)",
    },
    AliquotMethod.target_mass.value: {
        "label": "Target mass",
        "required_inputs": ["target_amount", "amount_unit_id"],
        "optional_inputs": ["concentration", "concentration_unit_id"],
        "stores": ["amount", "concentration"],
        "description": "Dest should receive target mass",
    },
    AliquotMethod.target_volume.value: {
        "label": "Target volume",
        "required_inputs": ["target_volume", "concentration", "concentration_unit_id"],
        "optional_inputs": ["volume_unit_id", "amount_unit_id"],
        "stores": ["amount", "concentration"],
        "description": "Target volume at known conc → mass to transfer",
    },
    AliquotMethod.target_concentration.value: {
        "label": "Target concentration",
        "required_inputs": ["target_concentration", "concentration_unit_id"],
        "optional_inputs": ["amount", "target_amount", "volume", "target_volume", "amount_unit_id"],
        "stores": ["amount", "concentration"],
        "description": "Set dest concentration; amount from mass or volume rule",
    },
    AliquotMethod.target_count.value: {
        "label": "Target count",
        "required_inputs": ["target_amount", "amount_unit_id"],
        "optional_inputs": [],
        "stores": ["amount"],
        "description": "Dest should receive target count",
    },
}


class AliquotPlanLine(BaseModel):
    """One plan row: source → dest transfer using a method."""
    line_id: Optional[str] = Field(None, description="Client-stable id for the plan row")
    method: AliquotMethod
    source_sample_id: UUID
    source_container_id: Optional[UUID] = None
    # Transfer inputs (method-specific)
    amount: Optional[float] = None
    amount_unit_id: Optional[UUID] = None
    volume: Optional[float] = None
    volume_unit_id: Optional[UUID] = None
    concentration: Optional[float] = None
    concentration_unit_id: Optional[UUID] = None
    target_amount: Optional[float] = None
    target_volume: Optional[float] = None
    target_concentration: Optional[float] = None
    # Destination
    dest_container_id: Optional[UUID] = None
    dest_container_type_id: Optional[UUID] = None
    dest_container_name: Optional[str] = None
    pool_group: Optional[str] = Field(
        None,
        description="Same pool_group → multi-content dest tube (one container, multiple samples)",
    )
    notes: Optional[str] = None


class AliquotPlanSaveRequest(BaseModel):
    lines: List[AliquotPlanLine] = Field(default_factory=list)


class AliquotPlanSaveResponse(BaseModel):
    entry_id: UUID
    lines: List[AliquotPlanLine]
    line_count: int


class ResolvedTransfer(BaseModel):
    line_id: Optional[str] = None
    method: AliquotMethod
    source_sample_id: UUID
    source_container_id: Optional[UUID] = None
    transfer_amount: float
    amount_unit_id: Optional[UUID] = None
    concentration: Optional[float] = None
    concentration_unit_id: Optional[UUID] = None
    pool_group: Optional[str] = None
    dest_container_id: Optional[UUID] = None
    dest_container_type_id: Optional[UUID] = None
    dest_container_name: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class AliquotExecuteRequest(BaseModel):
    """Execute plan lines (defaults to all saved plan lines on the entry)."""
    dry_run: bool = False
    lines: Optional[List[AliquotPlanLine]] = Field(
        None,
        description="If omitted, use entry.config.plan_lines",
    )


class AliquotExecuteLineResult(BaseModel):
    line_id: Optional[str] = None
    source_sample_id: UUID
    dest_sample_id: Optional[UUID] = None
    dest_container_id: Optional[UUID] = None
    transfer_amount: float
    amount_unit_id: Optional[UUID] = None
    concentration: Optional[float] = None
    status: str  # ok | dry_run | error
    message: Optional[str] = None


class AliquotExecuteResponse(BaseModel):
    entry_id: UUID
    dry_run: bool
    results: List[AliquotExecuteLineResult]
    success_count: int
    error_count: int


class AliquotMethodListResponse(BaseModel):
    methods: List[Dict[str, Any]]
