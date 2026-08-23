"""Schemas for concrete-method ELN aliquot/pool planning and execution."""

from enum import Enum
from typing import Optional, List, Any, Dict
from uuid import UUID
from pydantic import BaseModel, Field


class AliquotMethod(str, Enum):
    """Concrete Deiter IN methods; each implies exactly one mint operation."""

    aliquot_by_volume = "aliquot_by_volume"
    aliquot_by_target_amount = "aliquot_by_target_amount"
    aliquot_by_target_concentration = "aliquot_by_target_concentration"
    aliquot_n_way_equal_split = "aliquot_n_way_equal_split"
    pool_by_volume_per_source = "pool_by_volume_per_source"
    pool_equal_volume_each = "pool_equal_volume_each"
    pool_by_target_amount_per_source = "pool_by_target_amount_per_source"
    pool_consolidate_remaining = "pool_consolidate_remaining"


class AliquotOperation(str, Enum):
    """Destination transition operation."""

    aliquot = "aliquot"
    pool = "pool"


# Concrete method catalog. CUT methods are intentionally absent.
METHOD_PROFILES: Dict[str, Dict[str, Any]] = {
    AliquotMethod.aliquot_by_volume.value: {
        "label": "Aliquot — by volume",
        "mint_op": AliquotOperation.aliquot.value,
        "required_inputs": ["volume"],
        "optional_inputs": ["volume_unit_id", "amount_unit_id"],
        "description": "Transfer a volume using tracked source concentration",
    },
    AliquotMethod.aliquot_by_target_amount.value: {
        "label": "Aliquot — by target amount",
        "mint_op": AliquotOperation.aliquot.value,
        "required_inputs": ["target_amount"],
        "optional_inputs": ["amount_unit_id"],
        "description": "Transfer the requested target amount",
    },
    AliquotMethod.aliquot_by_target_concentration.value: {
        "label": "Aliquot — by target concentration (normalization)",
        "mint_op": AliquotOperation.aliquot.value,
        "required_inputs": ["target_concentration"],
        "optional_inputs": ["target_volume", "target_amount", "amount_unit_id"],
        "description": (
            "Normalize from a prior concentration result; requires destination "
            "volume or target amount"
        ),
    },
    AliquotMethod.aliquot_n_way_equal_split.value: {
        "label": "Aliquot — N-way equal split",
        "mint_op": AliquotOperation.aliquot.value,
        "required_inputs": ["split_count"],
        "optional_inputs": ["amount_unit_id"],
        "description": "Transfer one equal share of the tracked source amount",
    },
    AliquotMethod.pool_by_volume_per_source.value: {
        "label": "Pool — by volume per source",
        "mint_op": AliquotOperation.pool.value,
        "required_inputs": ["volume"],
        "optional_inputs": ["volume_unit_id", "amount_unit_id"],
        "description": "Transfer a specified volume from each source",
    },
    AliquotMethod.pool_equal_volume_each.value: {
        "label": "Pool — equal volume from each",
        "mint_op": AliquotOperation.pool.value,
        "required_inputs": ["volume"],
        "optional_inputs": ["volume_unit_id", "amount_unit_id"],
        "description": "Transfer the same volume from every source",
    },
    AliquotMethod.pool_by_target_amount_per_source.value: {
        "label": "Pool — by target amount per source",
        "mint_op": AliquotOperation.pool.value,
        "required_inputs": ["target_amount"],
        "optional_inputs": ["amount_unit_id"],
        "description": "Transfer a target amount from each source",
    },
    AliquotMethod.pool_consolidate_remaining.value: {
        "label": "Pool — consolidate remaining",
        "mint_op": AliquotOperation.pool.value,
        "required_inputs": [],
        "optional_inputs": [],
        "description": "Transfer all remaining tracked source amount",
    },
}


class AliquotPlanLine(BaseModel):
    """One source-to-destination row under the entry's concrete method."""

    line_id: Optional[str] = Field(
        None, description="Client-stable id for the plan row"
    )
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
    split_count: Optional[int] = Field(None, ge=2)
    # Destination
    dest_container_id: Optional[UUID] = None
    dest_container_type_id: Optional[UUID] = None
    dest_container_name: Optional[str] = None
    dest_sample_type: Optional[UUID] = None
    inherit_entry_dest_sample_type: bool = Field(
        True,
        description=(
            "True uses entry default; false with null dest_sample_type explicitly "
            "means Same as parent"
        ),
    )
    pool_group: Optional[str] = Field(
        None,
        description="Same pool_group → multi-content dest tube (one container, multiple samples)",
    )
    notes: Optional[str] = None


class AliquotPlanSaveRequest(BaseModel):
    method: AliquotMethod
    default_dest_sample_type: Optional[UUID] = None
    lines: List[AliquotPlanLine] = Field(default_factory=list)


class AliquotPlanSaveResponse(BaseModel):
    entry_id: UUID
    method: AliquotMethod
    default_dest_sample_type: Optional[UUID] = None
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
    dest_sample_type: Optional[UUID] = None
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


class SampleTypeOption(BaseModel):
    id: UUID
    name: str


class DestSampleTypeOptionsResponse(BaseModel):
    source_sample_type: SampleTypeOption
    operation: AliquotOperation
    options: List[SampleTypeOption]
