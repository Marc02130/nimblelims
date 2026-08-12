"""
Aliquot/pool plan resolution and execute (ELN entry predefined_action / plan).

Rules (Lab Ops L3–L4, L9):
  - Amount stored = mass or count only — never volume
  - by_volume / target_volume: convert via concentration → mass
  - Execute: reduce source Contents.amount; create dest sample + contents
  - pool_group: one dest container, multiple content rows
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.schemas.aliquot_plan import (
    AliquotMethod,
    AliquotPlanLine,
    AliquotPlanSaveRequest,
    AliquotPlanSaveResponse,
    ResolvedTransfer,
    AliquotExecuteRequest,
    AliquotExecuteResponse,
    AliquotExecuteLineResult,
    METHOD_PROFILES,
)
from models.entry import Entry, normalize_entry_type
from models.sample import Sample
from models.container import Container, Contents, ContainerType
from models.user import User
from models.list import ListEntry, List as ListModel


class AliquotPlanService:
    def __init__(
        self,
        db: Session,
        current_user: Optional[User] = None,
        *,
        auto_commit: bool = True,
    ) -> None:
        self.db = db
        self.current_user = current_user
        self.auto_commit = auto_commit

    def _user_id(self) -> Optional[UUID]:
        return self.current_user.id if self.current_user else None

    def list_methods(self) -> List[Dict[str, Any]]:
        out = []
        for key, prof in METHOD_PROFILES.items():
            out.append({"method": key, **prof})
        return out

    def _get_plan_entry(self, entry_id: UUID) -> Entry:
        entry = self.db.query(Entry).filter(Entry.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
        key = entry.predefined_entry_key
        if key not in (None, "aliquot_pool_plan") and normalize_entry_type(entry.entry_type) not in (
            "experiment_data",
            "predefined_action",
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entry is not an aliquot/pool plan entry",
            )
        # Allow experiment_data or predefined_action with aliquot key
        if key and key != "aliquot_pool_plan" and entry.entry_type == "predefined_action":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"predefined_entry_key {key} does not support aliquot execute",
            )
        return entry

    def save_plan(self, entry_id: UUID, data: AliquotPlanSaveRequest) -> AliquotPlanSaveResponse:
        entry = self._get_plan_entry(entry_id)
        lines = []
        for line in data.lines:
            d = line.model_dump(mode="json")
            if not d.get("line_id"):
                d["line_id"] = str(uuid4())
            # Validate method resolves (raises if invalid inputs)
            self.resolve_line(AliquotPlanLine.model_validate(d))
            lines.append(d)
        cfg = dict(entry.config or {})
        cfg["plan_lines"] = lines
        cfg["plan_updated_at"] = datetime.now(timezone.utc).isoformat()
        entry.config = cfg
        entry.modified_by = self._user_id()
        self.db.flush()
        if self.auto_commit:
            self.db.commit()
            self.db.refresh(entry)
        return AliquotPlanSaveResponse(
            entry_id=entry.id,
            lines=[AliquotPlanLine.model_validate(x) for x in lines],
            line_count=len(lines),
        )

    def get_plan(self, entry_id: UUID) -> AliquotPlanSaveResponse:
        entry = self._get_plan_entry(entry_id)
        raw = (entry.config or {}).get("plan_lines") or []
        lines = [AliquotPlanLine.model_validate(x) for x in raw]
        return AliquotPlanSaveResponse(entry_id=entry.id, lines=lines, line_count=len(lines))

    def resolve_line(self, line: AliquotPlanLine) -> ResolvedTransfer:
        """Compute transfer_amount (mass or count) from method inputs. Never stores volume."""
        warnings: List[str] = []
        method = line.method
        amount: Optional[float] = None
        conc = line.concentration
        conc_unit = line.concentration_unit_id
        amount_unit = line.amount_unit_id

        if method == AliquotMethod.by_mass:
            if line.amount is None:
                raise HTTPException(400, detail="by_mass requires amount")
            amount = float(line.amount)
        elif method == AliquotMethod.by_count:
            if line.amount is None:
                raise HTTPException(400, detail="by_count requires amount (count)")
            amount = float(line.amount)
        elif method == AliquotMethod.target_mass:
            if line.target_amount is None:
                raise HTTPException(400, detail="target_mass requires target_amount")
            amount = float(line.target_amount)
        elif method == AliquotMethod.target_count:
            if line.target_amount is None:
                raise HTTPException(400, detail="target_count requires target_amount")
            amount = float(line.target_amount)
        elif method == AliquotMethod.by_volume:
            if line.volume is None or line.concentration is None:
                raise HTTPException(
                    400,
                    detail="by_volume requires volume and concentration (mass = volume × conc)",
                )
            # amount = volume * concentration (same numeric base units assumed in v1)
            amount = float(line.volume) * float(line.concentration)
            conc = float(line.concentration)
            warnings.append("Volume not stored; mass computed as volume × concentration")
        elif method == AliquotMethod.target_volume:
            if line.target_volume is None or line.concentration is None:
                raise HTTPException(
                    400,
                    detail="target_volume requires target_volume and concentration",
                )
            amount = float(line.target_volume) * float(line.concentration)
            conc = float(line.concentration)
            warnings.append("Target volume converted to mass via concentration")
        elif method == AliquotMethod.target_concentration:
            if line.target_concentration is None:
                raise HTTPException(400, detail="target_concentration requires target_concentration")
            conc = float(line.target_concentration)
            if line.amount is not None:
                amount = float(line.amount)
            elif line.target_amount is not None:
                amount = float(line.target_amount)
            elif line.volume is not None:
                amount = float(line.volume) * conc
                warnings.append("Mass from volume × target concentration")
            elif line.target_volume is not None:
                amount = float(line.target_volume) * conc
                warnings.append("Mass from target_volume × target concentration")
            else:
                raise HTTPException(
                    400,
                    detail=(
                        "target_concentration requires amount, target_amount, "
                        "volume, or target_volume to size the transfer"
                    ),
                )
        else:
            raise HTTPException(400, detail=f"Unknown method {method}")

        if amount is None or amount <= 0:
            raise HTTPException(400, detail="Resolved transfer amount must be positive")

        return ResolvedTransfer(
            line_id=line.line_id,
            method=method,
            source_sample_id=line.source_sample_id,
            source_container_id=line.source_container_id,
            transfer_amount=amount,
            amount_unit_id=amount_unit,
            concentration=conc,
            concentration_unit_id=conc_unit or line.concentration_unit_id,
            pool_group=line.pool_group,
            dest_container_id=line.dest_container_id,
            dest_container_type_id=line.dest_container_type_id,
            dest_container_name=line.dest_container_name,
            warnings=warnings,
        )

    def execute(self, entry_id: UUID, data: AliquotExecuteRequest) -> AliquotExecuteResponse:
        entry = self._get_plan_entry(entry_id)
        if data.lines is not None:
            plan_lines = data.lines
        else:
            raw = (entry.config or {}).get("plan_lines") or []
            plan_lines = [AliquotPlanLine.model_validate(x) for x in raw]
        if not plan_lines:
            raise HTTPException(400, detail="No plan lines to execute")

        results: List[AliquotExecuteLineResult] = []
        # Pre-resolve all lines
        resolved: List[ResolvedTransfer] = []
        for line in plan_lines:
            try:
                resolved.append(self.resolve_line(line))
            except HTTPException as e:
                results.append(AliquotExecuteLineResult(
                    line_id=line.line_id,
                    source_sample_id=line.source_sample_id,
                    transfer_amount=0,
                    status="error",
                    message=str(e.detail),
                ))

        if data.dry_run:
            for r in resolved:
                results.append(AliquotExecuteLineResult(
                    line_id=r.line_id,
                    source_sample_id=r.source_sample_id,
                    transfer_amount=r.transfer_amount,
                    amount_unit_id=r.amount_unit_id,
                    concentration=r.concentration,
                    status="dry_run",
                    message="; ".join(r.warnings) if r.warnings else None,
                ))
            return AliquotExecuteResponse(
                entry_id=entry_id,
                dry_run=True,
                results=results,
                success_count=sum(1 for x in results if x.status == "dry_run"),
                error_count=sum(1 for x in results if x.status == "error"),
            )

        # Group by pool_group for multi-content dest
        pool_containers: Dict[str, UUID] = {}

        for r in resolved:
            try:
                dest_sample, dest_c = self._execute_transfer(r, pool_containers)
                results.append(AliquotExecuteLineResult(
                    line_id=r.line_id,
                    source_sample_id=r.source_sample_id,
                    dest_sample_id=dest_sample.id if dest_sample else None,
                    dest_container_id=dest_c.id if dest_c else None,
                    transfer_amount=r.transfer_amount,
                    amount_unit_id=r.amount_unit_id,
                    concentration=r.concentration,
                    status="ok",
                    message="; ".join(r.warnings) if r.warnings else None,
                ))
            except HTTPException as e:
                results.append(AliquotExecuteLineResult(
                    line_id=r.line_id,
                    source_sample_id=r.source_sample_id,
                    transfer_amount=r.transfer_amount,
                    status="error",
                    message=str(e.detail),
                ))
            except Exception as e:
                results.append(AliquotExecuteLineResult(
                    line_id=r.line_id,
                    source_sample_id=r.source_sample_id,
                    transfer_amount=r.transfer_amount,
                    status="error",
                    message=str(e),
                ))

        cfg = dict(entry.config or {})
        cfg["last_execute_at"] = datetime.now(timezone.utc).isoformat()
        cfg["last_execute_results"] = [x.model_dump(mode="json") for x in results]
        entry.config = cfg
        entry.modified_by = self._user_id()
        self.db.flush()
        if self.auto_commit:
            self.db.commit()

        return AliquotExecuteResponse(
            entry_id=entry_id,
            dry_run=False,
            results=results,
            success_count=sum(1 for x in results if x.status == "ok"),
            error_count=sum(1 for x in results if x.status == "error"),
        )

    def _find_source_content(
        self,
        sample_id: UUID,
        container_id: Optional[UUID],
    ) -> Contents:
        q = self.db.query(Contents).filter(Contents.sample_id == sample_id)
        if container_id:
            q = q.filter(Contents.container_id == container_id)
        content = q.first()
        if not content:
            raise HTTPException(
                400,
                detail=f"No container contents for sample {sample_id}"
                + (f" in container {container_id}" if container_id else ""),
            )
        return content

    def _available_status_id(self) -> UUID:
        sample_status_list = (
            self.db.query(ListModel).filter(ListModel.name == "sample_status").first()
        )
        if sample_status_list:
            available = (
                self.db.query(ListEntry)
                .filter(
                    ListEntry.list_id == sample_status_list.id,
                    ListEntry.name == "Available for Testing",
                )
                .first()
            )
            if available:
                return available.id
        # Fallback: any list entry named Available for Testing
        available = (
            self.db.query(ListEntry)
            .filter(ListEntry.name == "Available for Testing")
            .first()
        )
        if available:
            return available.id
        raise HTTPException(
            400,
            detail="Sample status 'Available for Testing' not found in configuration",
        )

    def _execute_transfer(
        self,
        r: ResolvedTransfer,
        pool_containers: Dict[str, UUID],
    ) -> Tuple[Sample, Container]:
        parent = self.db.query(Sample).filter(Sample.id == r.source_sample_id).first()
        if not parent:
            raise HTTPException(404, detail=f"Source sample {r.source_sample_id} not found")

        content = self._find_source_content(r.source_sample_id, r.source_container_id)
        current = float(content.amount) if content.amount is not None else None
        if current is not None and r.transfer_amount > current:
            raise HTTPException(
                400,
                detail=(
                    f"Insufficient amount on source contents: have {current}, "
                    f"need {r.transfer_amount}"
                ),
            )
        if current is not None:
            content.amount = Decimal(str(current - r.transfer_amount))
        # If amount was null, still create dest (lab may not track source amount yet)

        # Destination container
        dest_c: Optional[Container] = None
        if r.pool_group and r.pool_group in pool_containers:
            dest_c = self.db.query(Container).filter(
                Container.id == pool_containers[r.pool_group]
            ).first()
        elif r.dest_container_id:
            dest_c = self.db.query(Container).filter(
                Container.id == r.dest_container_id, Container.active == True  # noqa: E712
            ).first()
            if not dest_c:
                raise HTTPException(400, detail="dest_container_id not found")
        else:
            type_id = r.dest_container_type_id
            if not type_id:
                # default to source container type
                src_c = self.db.query(Container).filter(
                    Container.id == content.container_id
                ).first()
                type_id = src_c.type_id if src_c else None
            if not type_id:
                raise HTTPException(
                    400,
                    detail="dest_container_type_id required when dest_container_id omitted",
                )
            name = r.dest_container_name or f"ALIQUOT-{uuid4().hex[:8]}"
            dest_c = Container(
                name=name,
                type_id=type_id,
                created_by=self._user_id(),
                modified_by=self._user_id(),
            )
            self.db.add(dest_c)
            self.db.flush()

        if r.pool_group and r.pool_group not in pool_containers:
            pool_containers[r.pool_group] = dest_c.id

        # New dest sample (child of source)
        status_id = self._available_status_id()
        dest_sample = Sample(
            name=f"{parent.name}-ALQ-{uuid4().hex[:6]}" if parent.name else f"ALQ-{uuid4().hex[:8]}",
            description=f"Aliquot from {parent.name or parent.id} ({r.method.value})",
            sample_type=parent.sample_type,
            status=status_id,
            matrix=parent.matrix,
            temperature=parent.temperature,
            parent_sample_id=parent.id,
            project_id=parent.project_id,
            qc_type=parent.qc_type,
            due_date=parent.due_date,
            received_date=parent.received_date,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        self.db.add(dest_sample)
        self.db.flush()

        # Dest contents amount = transfer (mass/count); conc from plan when present
        dest_amount = Decimal(str(r.transfer_amount))
        dest_conc = Decimal(str(r.concentration)) if r.concentration is not None else content.concentration
        dest_conc_units = r.concentration_unit_id or content.concentration_units
        amount_units = r.amount_unit_id or content.amount_units

        # If pool already has this sample, sum amount
        existing_dest = (
            self.db.query(Contents)
            .filter(
                Contents.container_id == dest_c.id,
                Contents.sample_id == dest_sample.id,
            )
            .first()
        )
        if existing_dest:
            if existing_dest.amount is not None:
                existing_dest.amount = Decimal(str(float(existing_dest.amount) + float(dest_amount)))
            else:
                existing_dest.amount = dest_amount
        else:
            self.db.add(Contents(
                container_id=dest_c.id,
                sample_id=dest_sample.id,
                amount=dest_amount,
                amount_units=amount_units,
                concentration=dest_conc,
                concentration_units=dest_conc_units,
            ))
        self.db.flush()
        return dest_sample, dest_c
