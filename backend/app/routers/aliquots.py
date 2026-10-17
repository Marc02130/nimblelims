"""
Aliquots and derivatives router for NimbleLims.

An aliquot is the same sample in another container: no new Sample row.
A derivative changes the sample type, creates a child named ``{parent}-DER-{token}``,
and is allowed only by an active sample_type_transitions row with operation
``derivative``. Both calls debit the source vessel in one atomic UPDATE and
leave that row in place when the remainder is zero.
"""
from decimal import Decimal
from typing import Callable, List, Optional, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.conversions import (
    ConversionError,
    convert_to_base_unit,
    reporting_unit,
    require_base_unit_named,
)
from app.core.rbac import require_sample_create, require_sample_read
from app.database import get_db
from app.schemas.aliquot import (
    AliquotCreateRequest,
    AliquotResponse,
    DerivativeCreateRequest,
    DerivativeResponse,
    PoolingRequest,
    PoolingResponse,
)
from app.services.contents_amount import debit_contents_amount
from app.services.sample_naming import minted_child_name
from models.container import Container, Contents
from models.sample import Sample, SampleTypeTransition
from models.unit import Unit
from models.user import User

router = APIRouter()

T = TypeVar("T")


def _http(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _with_contents(
    sample: Sample,
    db: Session,
    schema,
    contents: Optional[Contents] = None,
    source_container_id: Optional[UUID] = None,
    source_amount_remaining: Optional[Decimal] = None,
):
    """Build an Aliquot/DerivativeResponse including container/amount/client.

    ``schema.from_orm(sample)`` left container_id, concentration, amount (and
    their units) and client_id null on every response: those live on the
    ``contents`` row and the project, not on Sample.
    """
    data = schema.model_validate(sample, from_attributes=True).model_dump()
    if contents is None:
        contents = (
            db.query(Contents)
            .filter(Contents.sample_id == sample.id)
            .order_by(Contents.container_id)
            .first()
        )
    if contents is not None:
        data.update(
            container_id=contents.container_id,
            concentration=float(contents.concentration) if contents.concentration is not None else None,
            concentration_units=contents.concentration_units,
            amount=float(contents.amount) if contents.amount is not None else None,
            amount_units=contents.amount_units,
        )
    if source_container_id is not None:
        data["source_container_id"] = source_container_id
    if source_amount_remaining is not None:
        data["source_amount_remaining"] = float(source_amount_remaining)
    project = getattr(sample, "project", None)
    if project is not None and data.get("client_id") is None:
        data["client_id"] = getattr(project, "client_id", None)
    return schema(**data)


def _load_parent(db: Session, sample_id: UUID, current_user: User) -> Sample:
    parent = db.query(Sample).filter(Sample.id == sample_id, Sample.active == True).first()  # noqa: E712
    if not parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent sample not found")
    if current_user.role.name != "Administrator":
        if current_user.client_id and parent.project.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient project permissions",
            )
    return parent


def _active_container(db: Session, container_id: UUID) -> Container:
    container = db.query(Container).filter(
        Container.id == container_id,
        Container.active == True,  # noqa: E712
    ).first()
    if not container:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Container not found")
    return container


def _positive_amount(amount: Optional[float]) -> Decimal:
    if amount is None or amount <= 0:
        raise _http(
            status.HTTP_400_BAD_REQUEST,
            "amount_required",
            "A positive amount is required so the source vessel can be debited.",
        )
    return Decimal(str(amount))


def _resolve_source(
    db: Session,
    sample_id: UUID,
    dest_container_id: UUID,
    source_container_id: Optional[UUID],
) -> Contents:
    """Pick the vessel to debit. Never the destination container."""
    if source_container_id is not None:
        if source_container_id == dest_container_id:
            raise _http(
                status.HTTP_400_BAD_REQUEST,
                "aliquot_same_container",
                "The destination container must be a different vessel from the source.",
            )
        row = (
            db.query(Contents)
            .filter(Contents.sample_id == sample_id, Contents.container_id == source_container_id)
            .first()
        )
        if row is None:
            raise _http(
                status.HTTP_400_BAD_REQUEST,
                "source_contents_missing",
                "The source container does not hold this sample.",
            )
        return row

    rows = (
        db.query(Contents)
        .filter(Contents.sample_id == sample_id)
        .order_by(Contents.container_id)
        .all()
    )
    others = [row for row in rows if row.container_id != dest_container_id]
    if len(others) == 1:
        return others[0]
    if len(others) > 1:
        raise _http(
            status.HTTP_400_BAD_REQUEST,
            "source_container_required",
            "This sample is in more than one container. Pass source_container_id.",
        )
    if rows:
        raise _http(
            status.HTTP_409_CONFLICT,
            "sample_already_in_container",
            "This sample is already in the destination container.",
        )
    raise _http(
        status.HTTP_400_BAD_REQUEST,
        "source_contents_missing",
        "Parent sample has no tracked contents to draw from.",
    )


def _amount_units(source: Contents, requested: Optional[UUID]) -> Optional[UUID]:
    if requested is not None and source.amount_units is not None and requested != source.amount_units:
        raise _http(
            status.HTTP_400_BAD_REQUEST,
            "amount_unit_mismatch",
            "Amount units must match the source vessel. This call does not convert units.",
        )
    return requested or source.amount_units


def _commit_transfer(db: Session, mutate: Callable[[], T]) -> T:
    """Run the debit and the destination insert in one savepoint, then commit.

    A refusal rolls the savepoint back so a failed draw does not stick. The
    contents row is never deleted; a full draw leaves amount 0.
    """
    nested = db.begin_nested()
    try:
        result = mutate()
        db.flush()
        nested.commit()
    except HTTPException:
        nested.rollback()
        raise
    except IntegrityError:
        nested.rollback()
        raise
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def _available_status_id(db: Session) -> UUID:
    from models.list import List as ListModel
    from models.list import ListEntry

    sample_status_list = db.query(ListModel).filter(ListModel.name == "sample_status").first()
    available_status = None
    if sample_status_list:
        available_status = db.query(ListEntry).filter(
            ListEntry.list_id == sample_status_list.id,
            ListEntry.name == "Available for Testing",
        ).first()
    if not available_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample status 'Available for Testing' not found in configuration",
        )
    return available_status.id


def _place_contents(
    db: Session,
    container_id: UUID,
    sample_id: UUID,
    amount: Decimal,
    amount_units: Optional[UUID],
    concentration: Optional[float],
    concentration_units: Optional[UUID],
    source: Contents,
) -> Contents:
    existing = (
        db.query(Contents)
        .filter(Contents.container_id == container_id, Contents.sample_id == sample_id)
        .first()
    )
    if existing is not None:
        raise _http(
            status.HTTP_409_CONFLICT,
            "sample_already_in_container",
            "This sample is already in the destination container.",
        )
    dest_concentration = concentration if concentration is not None else source.concentration
    dest_concentration_units = concentration_units or source.concentration_units
    contents = Contents(
        container_id=container_id,
        sample_id=sample_id,
        concentration=dest_concentration,
        concentration_units=dest_concentration_units,
        amount=amount,
        amount_units=amount_units,
    )
    db.add(contents)
    return contents


def _debit_quantity(db: Session, source: Contents, requested: float, requested_unit: Unit) -> Decimal:
    """Request amount expressed in the source vessel's unit.

    The atomic debit compares numbers, so a microliter request against a
    milliliter vessel is converted first. A unitless source is debited by the
    request number.
    """
    if source.amount_units is None or source.amount_units == requested_unit.id:
        return Decimal(str(requested))
    source_unit = (
        db.query(Unit)
        .filter(Unit.id == source.amount_units, Unit.active == True)  # noqa: E712
        .first()
    )
    if (
        source_unit is None
        or source_unit.type != requested_unit.type
        or source_unit.multiplier is None
        or requested_unit.multiplier is None
    ):
        raise _http(
            status.HTTP_400_BAD_REQUEST,
            "amount_unit_mismatch",
            "Pool amount units must match the source vessel or share its unit type.",
        )
    source_multiplier = Decimal(str(source_unit.multiplier))
    if source_multiplier == 0:
        raise _http(
            status.HTTP_400_BAD_REQUEST,
            "amount_unit_mismatch",
            "Source amount unit has a zero multiplier.",
        )
    base = Decimal(str(requested)) * Decimal(str(requested_unit.multiplier))
    return base / source_multiplier


@router.post("", response_model=AliquotResponse)
def create_aliquot(
    aliquot_data: AliquotCreateRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db),
) -> AliquotResponse:
    """
    Place the parent sample in a new container and debit the source vessel.

    The response ``id`` is the parent sample. No Sample row is inserted.
    """
    parent_sample = _load_parent(db, aliquot_data.parent_sample_id, current_user)
    if aliquot_data.sample_type is not None and aliquot_data.sample_type != parent_sample.sample_type:
        raise _http(
            status.HTTP_400_BAD_REQUEST,
            "aliquot_type_change_not_allowed",
            "An aliquot keeps the parent's sample type. Create a derivative to change the sample type.",
        )
    _active_container(db, aliquot_data.container_id)
    transfer = _positive_amount(aliquot_data.amount)
    source = _resolve_source(db, parent_sample.id, aliquot_data.container_id, aliquot_data.source_container_id)
    units = _amount_units(source, aliquot_data.amount_units)

    def mutate() -> AliquotResponse:
        remaining = debit_contents_amount(
            db, source, transfer, sample_label=str(parent_sample.id)
        )
        dest = _place_contents(
            db,
            aliquot_data.container_id,
            parent_sample.id,
            transfer,
            units,
            aliquot_data.concentration,
            aliquot_data.concentration_units,
            source,
        )
        return _with_contents(
            parent_sample,
            db,
            AliquotResponse,
            contents=dest,
            source_container_id=source.container_id,
            source_amount_remaining=remaining,
        )

    return _commit_transfer(db, mutate)


@router.post("/aliquot", response_model=AliquotResponse, include_in_schema=False)
def create_aliquot_legacy(
    aliquot_data: AliquotCreateRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db),
) -> AliquotResponse:
    """Legacy path alias for create_aliquot."""
    return create_aliquot(aliquot_data, current_user, db)


@router.post("/derivative", response_model=DerivativeResponse)
def create_derivative(
    derivative_data: DerivativeCreateRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db),
) -> DerivativeResponse:
    """
    Create a derivative child sample and debit the parent's source vessel.

    The child name is ``{parent}-DER-{token}``. The caller's ``name`` is a
    label, stored as the description only when description is omitted.
    """
    parent_sample = _load_parent(db, derivative_data.parent_sample_id, current_user)
    if derivative_data.sample_type == parent_sample.sample_type:
        raise _http(
            status.HTTP_400_BAD_REQUEST,
            "derivative_same_type",
            "A derivative must change the sample type. Use an aliquot for the same sample type.",
        )
    allowed = (
        db.query(SampleTypeTransition.id)
        .filter(
            SampleTypeTransition.client_id == parent_sample.project.client_id,
            SampleTypeTransition.source_sample_type == parent_sample.sample_type,
            SampleTypeTransition.operation == "derivative",
            SampleTypeTransition.allowed_dest_sample_type == derivative_data.sample_type,
            SampleTypeTransition.active.is_(True),
        )
        .first()
    )
    if allowed is None:
        raise _http(
            status.HTTP_400_BAD_REQUEST,
            "dest_sample_type_not_allowed",
            "This sample type change is not an allowed derivative transition "
            "for the client (Sample type transitions).",
        )
    _active_container(db, derivative_data.container_id)
    status_id = _available_status_id(db)
    transfer = _positive_amount(derivative_data.amount)
    source = _resolve_source(
        db, parent_sample.id, derivative_data.container_id, derivative_data.source_container_id
    )
    units = _amount_units(source, derivative_data.amount_units)
    description = derivative_data.description or derivative_data.name

    def mutate() -> DerivativeResponse:
        remaining = debit_contents_amount(
            db, source, transfer, sample_label=str(parent_sample.id)
        )
        derivative = Sample(
            name=minted_child_name(parent_sample.name, "DER"),
            description=description,
            due_date=parent_sample.due_date,
            received_date=parent_sample.received_date,
            sample_type=derivative_data.sample_type,
            status=status_id,
            matrix=parent_sample.matrix,
            temperature=(
                derivative_data.temperature
                if derivative_data.temperature is not None
                else parent_sample.temperature
            ),
            parent_sample_id=parent_sample.id,
            project_id=parent_sample.project_id,
            qc_type=derivative_data.qc_type or parent_sample.qc_type,
            created_by=current_user.id,
            modified_by=current_user.id,
        )
        db.add(derivative)
        db.flush()
        db.refresh(derivative)
        dest = _place_contents(
            db,
            derivative_data.container_id,
            derivative.id,
            transfer,
            units,
            derivative_data.concentration,
            derivative_data.concentration_units,
            source,
        )
        return _with_contents(
            derivative,
            db,
            DerivativeResponse,
            contents=dest,
            source_container_id=source.container_id,
            source_amount_remaining=remaining,
        )

    return _commit_transfer(db, mutate)


@router.post("/pool", response_model=PoolingResponse)
def pool_samples(
    pooling_data: PoolingRequest,
    current_user: User = Depends(require_sample_create),
    db: Session = Depends(get_db)
):
    """
    Pool samples into one container and debit every source vessel.

    The debits and the destination rows commit together. One refusal rolls
    the whole call back. A full draw leaves the source contents row at amount 0.

    The summary concentration is the type's base unit (multiplier 1). Mixed
    units of one type convert through that base. A different unit type, such
    as endotoxin activity or a copy count, does not convert onto it. Plan
    execute is the bench pool; this route places the existing samples and
    does not mint a child.
    """
    # Verify container exists
    container = db.query(Container).filter(
        Container.id == pooling_data.container_id,
        Container.active == True
    ).first()
    
    if not container:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container not found"
        )
    
    # Verify all samples exist and user has access
    samples = db.query(Sample).filter(
        Sample.id.in_(pooling_data.samples),
        Sample.active == True
    ).all()
    
    if len(samples) != len(pooling_data.samples):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more samples not found"
        )
    
    # Check project access for all samples
    if current_user.role.name != "Administrator":
        for sample in samples:
            if current_user.client_id and sample.project.client_id != current_user.client_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: insufficient project permissions"
                )
    
    # Amount and concentration stay in the unit the vessels already use.
    # A single base unit, when the type has one, is only the conversion scale.
    amount_rows: List[Unit] = []
    concentration_rows: List[Unit] = []

    for i, sample_id in enumerate(pooling_data.samples):
        amount_unit = db.query(Unit).filter(Unit.id == pooling_data.amount_units[i]).first()
        concentration_unit = db.query(Unit).filter(
            Unit.id == pooling_data.concentration_units[i]
        ).first()
        if not amount_unit or not concentration_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid units for sample {sample_id}",
            )
        if pooling_data.concentrations[i] == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot pool: concentration is zero",
            )
        if pooling_data.amounts[i] <= 0:
            raise _http(
                status.HTTP_400_BAD_REQUEST,
                "amount_required",
                "A positive amount is required so the source vessel can be debited.",
            )
        amount_rows.append(amount_unit)
        concentration_rows.append(concentration_unit)

    draws = []
    for i, sample_id in enumerate(pooling_data.samples):
        source_container_id = None
        if pooling_data.source_container_ids is not None:
            source_container_id = pooling_data.source_container_ids[i]
        source = _resolve_source(db, sample_id, pooling_data.container_id, source_container_id)
        draws.append((sample_id, source, amount_rows[i], concentration_rows[i]))

    amount_units = list(amount_rows)
    concentration_units = list(concentration_rows)
    for _sample_id, source, _amount_unit, _concentration_unit in draws:
        if source.amount_units is not None:
            source_amount_unit = (
                db.query(Unit)
                .filter(Unit.id == source.amount_units, Unit.active == True)  # noqa: E712
                .first()
            )
            if source_amount_unit is None:
                raise _http(
                    status.HTTP_400_BAD_REQUEST,
                    "amount_unit_mismatch",
                    "Source amount unit is missing or inactive.",
                )
            amount_units.append(source_amount_unit)
        if source.concentration_units is not None:
            source_concentration_unit = (
                db.query(Unit)
                .filter(Unit.id == source.concentration_units, Unit.active == True)  # noqa: E712
                .first()
            )
            if source_concentration_unit is None:
                raise _http(
                    status.HTTP_400_BAD_REQUEST,
                    "incompatible_units",
                    "Source concentration unit is missing or inactive.",
                )
            concentration_units.append(source_concentration_unit)

    try:
        amount_report, amount_to_base = reporting_unit(db, amount_units, "amount")
        concentration_report, concentration_to_base = reporting_unit(
            db, concentration_units, "concentration"
        )
    except ConversionError as exc:
        raise _http(
            status.HTTP_400_BAD_REQUEST,
            "incompatible_units",
            str(exc),
        ) from exc

    def _reported(value: float, unit: Unit, to_base: bool) -> float:
        if not to_base:
            return float(value)
        return convert_to_base_unit(float(value), str(unit.id), db)

    try:
        total_volume = 0.0
        total_concentration = 0.0
        for i, _sample_id in enumerate(pooling_data.samples):
            amount_value = _reported(pooling_data.amounts[i], amount_rows[i], amount_to_base)
            concentration_value = _reported(
                pooling_data.concentrations[i], concentration_rows[i], concentration_to_base
            )
            if concentration_value == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot pool: concentration is zero",
                )
            volume = amount_value / concentration_value
            total_volume += volume
            total_concentration += concentration_value * volume
    except ConversionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    average_concentration = total_concentration / total_volume if total_volume > 0 else 0
    try:
        volume_unit_id = require_base_unit_named(db, "volume").id
    except ConversionError:
        volume_unit_id = amount_report.id

    debits = []
    for i, (sample_id, source, amount_unit, _concentration_unit) in enumerate(draws):
        debits.append(
            (
                sample_id,
                source,
                _debit_quantity(db, source, pooling_data.amounts[i], amount_unit),
            )
        )

    def mutate() -> PoolingResponse:
        # Lock sources in a stable order so two pools cannot deadlock.
        for _sample_id, source, transfer in sorted(
            debits, key=lambda item: (str(item[1].container_id), str(item[1].sample_id))
        ):
            debit_contents_amount(db, source, transfer, sample_label=str(_sample_id))
        for i, (sample_id, source, _transfer) in enumerate(debits):
            # The destination holds the mixture concentration in the shared
            # reporting unit, not each source's requested concentration.
            # The amount is the quantity that moved, in the shared amount unit.
            if amount_to_base:
                placed_amount = Decimal(str(_reported(
                    pooling_data.amounts[i], amount_rows[i], True
                )))
                placed_amount_unit = amount_report.id
            else:
                placed_amount = Decimal(str(pooling_data.amounts[i]))
                placed_amount_unit = pooling_data.amount_units[i]
            _place_contents(
                db,
                pooling_data.container_id,
                sample_id,
                placed_amount,
                placed_amount_unit,
                average_concentration,
                concentration_report.id,
                source,
            )
        return PoolingResponse(
            container_id=pooling_data.container_id,
            pooled_samples=pooling_data.samples,
            total_volume=total_volume,
            total_volume_units=volume_unit_id,
            average_concentration=average_concentration,
            concentration_units=concentration_report.id,
            notes=pooling_data.notes,
        )

    return _commit_transfer(db, mutate)


@router.get("/parent/{parent_sample_id}", response_model=List[AliquotResponse])
def get_aliquots_for_parent(
    parent_sample_id: UUID,
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    List every container that holds this sample.

    An aliquot is another contents row of the same sample, so each row in the
    response has this sample's id and a different container_id. Legacy same-type
    child samples are not listed; they are not aliquots.
    """
    parent_sample = _load_parent(db, parent_sample_id, current_user)
    rows = (
        db.query(Contents)
        .filter(Contents.sample_id == parent_sample_id)
        .order_by(Contents.container_id)
        .all()
    )
    return [
        _with_contents(parent_sample, db, AliquotResponse, contents=row)
        for row in rows
    ]


@router.get("/derivatives/{parent_sample_id}", response_model=List[DerivativeResponse])
def get_derivatives_for_parent(
    parent_sample_id: UUID,
    current_user: User = Depends(require_sample_read),
    db: Session = Depends(get_db)
):
    """
    Get all derivatives for a parent sample.
    """
    parent_sample = _load_parent(db, parent_sample_id, current_user)

    # Get derivatives (child samples with different sample_type from parent)
    derivatives = db.query(Sample).filter(
        Sample.parent_sample_id == parent_sample_id,
        Sample.sample_type != parent_sample.sample_type,  # Different type = derivative
        Sample.active == True
    ).all()
    
    return [_with_contents(derivative, db, DerivativeResponse) for derivative in derivatives]
