"""
Pydantic schemas for aliquots and derivatives
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class AliquotCreateRequest(BaseModel):
    """Place the parent sample in another container. No new Sample row is created."""
    parent_sample_id: UUID = Field(..., description="ID of the sample to place in the destination container")
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="Ignored. An aliquot does not create or rename a sample.",
    )
    description: Optional[str] = Field(
        None,
        description="Ignored. An aliquot does not create a sample.",
    )
    container_id: UUID = Field(..., description="Destination container. Must not already hold this sample.")
    source_container_id: Optional[UUID] = Field(
        None,
        description=(
            "Vessel to debit. Required when the sample is already in more than one container."
        ),
    )
    concentration: Optional[float] = Field(None, ge=0, description="Concentration of the aliquot")
    concentration_units: Optional[UUID] = Field(None, description="ID of concentration units")
    amount: Optional[float] = Field(
        None,
        ge=0,
        description="Amount to move into the destination container. Must be positive.",
    )
    amount_units: Optional[UUID] = Field(
        None,
        description="Must match the source vessel when the source vessel has units.",
    )
    temperature: Optional[float] = Field(
        None,
        description="Ignored. Temperature stays on the sample and is not changed by an aliquot.",
    )
    qc_type: Optional[UUID] = Field(
        None,
        description="Ignored. An aliquot does not create a sample and does not change qc_type.",
    )
    sample_type: Optional[UUID] = Field(
        None,
        description=(
            "Optional. An aliquot keeps the parent's sample type; any other value is "
            "refused (use a derivative to change type)."
        ),
    )

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < -273.15 or v > 1000):
            raise ValueError('Temperature must be between -273.15°C and 1000°C')
        return v


class DerivativeCreateRequest(BaseModel):
    """Create a child sample of a different type. The child is named ``{parent}-DER-{token}``."""
    parent_sample_id: UUID = Field(..., description="ID of parent sample")
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description=(
            "Caller label. The stored sample name is {parent}-DER-{token}. "
            "This value is saved as the description only when description is omitted."
        ),
    )
    description: Optional[str] = Field(None, description="Description of the derivative")
    sample_type: UUID = Field(..., description="ID of sample type from list_entries")
    container_id: UUID = Field(..., description="ID of container for the derivative")
    source_container_id: Optional[UUID] = Field(
        None,
        description=(
            "Vessel to debit. Required when the parent is already in more than one container."
        ),
    )
    concentration: Optional[float] = Field(None, ge=0, description="Concentration of the derivative")
    concentration_units: Optional[UUID] = Field(None, description="ID of concentration units")
    amount: Optional[float] = Field(None, ge=0, description="Amount of the derivative")
    amount_units: Optional[UUID] = Field(None, description="ID of amount units")
    temperature: Optional[float] = Field(None, description="Temperature of the derivative")
    qc_type: Optional[UUID] = Field(None, description="ID of QC type from list_entries")

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < -273.15 or v > 1000):
            raise ValueError('Temperature must be between -273.15°C and 1000°C')
        return v


class AliquotResponse(BaseModel):
    """One container placement of a sample. ``id`` is that sample; no child row is created."""
    id: UUID
    name: str
    description: Optional[str] = None
    parent_sample_id: Optional[UUID] = None
    sample_type: Optional[UUID] = None
    project_id: UUID
    client_id: Optional[UUID] = None
    container_id: Optional[UUID] = None
    source_container_id: Optional[UUID] = None
    source_amount_remaining: Optional[float] = None
    concentration: Optional[float] = None
    concentration_units: Optional[UUID] = None
    amount: Optional[float] = None
    amount_units: Optional[UUID] = None
    temperature: Optional[float] = None
    qc_type: Optional[UUID] = None
    status: Optional[UUID] = None
    active: bool
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class DerivativeResponse(BaseModel):
    """Schema for derivative response"""
    id: UUID
    name: str
    description: Optional[str] = None
    parent_sample_id: Optional[UUID] = None
    project_id: UUID
    client_id: Optional[UUID] = None
    sample_type: Optional[UUID] = None
    container_id: Optional[UUID] = None
    source_container_id: Optional[UUID] = None
    source_amount_remaining: Optional[float] = None
    concentration: Optional[float] = None
    concentration_units: Optional[UUID] = None
    amount: Optional[float] = None
    amount_units: Optional[UUID] = None
    temperature: Optional[float] = None
    qc_type: Optional[UUID] = None
    status: Optional[UUID] = None
    active: bool
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_at: datetime
    modified_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class PoolingRequest(BaseModel):
    """Schema for pooling samples in a container"""
    container_id: UUID = Field(..., description="ID of container")
    samples: List[UUID] = Field(..., min_items=2, description="List of sample IDs to pool")
    concentrations: List[float] = Field(..., description="Concentrations for each sample")
    concentration_units: List[UUID] = Field(..., description="Concentration units for each sample")
    amounts: List[float] = Field(..., description="Amounts for each sample")
    amount_units: List[UUID] = Field(..., description="Amount units for each sample")
    source_container_ids: Optional[List[UUID]] = Field(
        None,
        description=(
            "Vessel to debit for each sample, in the same order as samples. "
            "Required for a sample that is already in more than one vessel."
        ),
    )
    notes: Optional[str] = Field(None, description="Notes about the pooling")

    @validator('samples', 'concentrations', 'concentration_units', 'amounts', 'amount_units')
    def validate_list_lengths(cls, v, values):
        if 'samples' in values and len(v) != len(values['samples']):
            raise ValueError('All lists must have the same length')
        return v

    @validator('source_container_ids')
    def validate_source_container_ids(cls, v, values):
        if v is None:
            return v
        samples = values.get('samples')
        if samples is not None and len(v) != len(samples):
            raise ValueError('source_container_ids must have the same length as samples')
        return v

    @validator('concentrations', 'amounts')
    def validate_positive_values(cls, v):
        if any(val < 0 for val in v):
            raise ValueError('Concentrations and amounts must be non-negative')
        return v


class PoolingResponse(BaseModel):
    """Schema for pooling response"""
    container_id: UUID
    pooled_samples: List[UUID]
    total_volume: Optional[float] = Field(None, description="Total volume after pooling")
    total_volume_units: Optional[UUID] = Field(None, description="Units for total volume")
    average_concentration: Optional[float] = Field(None, description="Average concentration")
    concentration_units: Optional[UUID] = Field(None, description="Units for average concentration")
    notes: Optional[str]

    class Config:
        from_attributes = True
