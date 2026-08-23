"""
Service for Experiment Entries (P0 foundation).

Template declaration: ExperimentTemplate.template_definition['entries']

Write-back policy:
  - Off by default; map on entry_field_definitions.write_back_target
  - Applied only on entry submit (not save)
  - SAMPLE_WRITE_BACK_COLUMNS allowlist (identity/accessioning excluded)
  - Last write wins; previous value on EntryFieldValue.write_back_previous
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.repositories.entry_repository import EntryRepository
from app.schemas.entry import (
    EntryCreate,
    EntryUpdate,
    EntryFieldValueUpsert,
    InstantiateEntriesRequest,
    EntryGridResponse,
    EntryGridColumn,
    EntryGridRow,
    EntryGridCell,
    EntryGridMeta,
    EntryExportResponse,
    EntryExportRow,
    EntrySubmitResponse,
    EntryRead,
)
from app.schemas.aliquot_plan import AliquotMethod
from models.entry import (
    Entry,
    EntryFieldValue,
    ENTRY_TYPES,
    SAMPLE_WRITE_BACK_COLUMNS,
    SAMPLE_SYSTEM_FIELDS,
    PREDEFINED_ENTRY_DEFAULTS,
    normalize_entry_type,
    is_sample_scoped_entry,
    is_experiment_scoped_entry,
    READ_ONLY_ENTRY_TYPES,
)
from models.sample import Sample
from models.experiment import ExperimentSampleExecution
from models.list import ListEntry
from models.user import User


class EntryService:
    def __init__(
        self,
        db: Session,
        current_user: Optional[User] = None,
        *,
        auto_commit: bool = True,
    ) -> None:
        self.db = db
        self.repo = EntryRepository(db)
        self.current_user = current_user
        self.auto_commit = auto_commit

    def _user_id(self) -> Optional[UUID]:
        return self.current_user.id if self.current_user else None

    def _commit_refresh(self, *objects: Any) -> None:
        self.db.flush()
        for obj in objects:
            if obj is not None:
                try:
                    self.db.refresh(obj)
                except Exception:
                    pass
        if self.auto_commit:
            self.db.commit()

    def get_entry(self, entry_id: UUID) -> Entry:
        e = self.repo.get_entry(entry_id)
        if not e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found"
            )
        return e

    def list_entries(
        self,
        experiment_id: UUID,
        active: Optional[bool] = True,
        include_values: bool = False,
    ) -> List[Entry]:
        if not self.repo.get_experiment(experiment_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found",
            )
        return self.repo.list_for_experiment(
            experiment_id,
            active=active,
            load_values=include_values,
        )

    def create_entry(self, data: EntryCreate) -> Entry:
        if data.entry_type not in ENTRY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid entry_type; allowed: {sorted(ENTRY_TYPES)}",
            )
        entry_type = normalize_entry_type(data.entry_type)
        if not self.repo.get_experiment(data.experiment_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found",
            )
        config = dict(data.config or {})
        config.setdefault("status", "draft")
        entry = self.repo.create_entry(
            experiment_id=data.experiment_id,
            entry_type=entry_type,
            name=data.name,
            description=data.description,
            predefined_entry_key=data.predefined_entry_key,
            sort_order=data.sort_order or 0,
            config=config,
            process_step_id=data.process_step_id,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        if data.fields:
            for f in data.fields:
                self._add_field_link(
                    entry.id,
                    f.field_definition_id,
                    f.sort_order or 0,
                    f.visible,
                    f.write_back_target,
                )
        self._commit_refresh(entry)
        return self.get_entry(entry.id)

    def _add_field_link(
        self,
        entry_id: UUID,
        field_definition_id: UUID,
        sort_order: int,
        visible: bool,
        write_back_target: Optional[str],
    ) -> None:
        if not self.repo.field_definition_exists(field_definition_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FieldDefinition {field_definition_id} not found",
            )
        if write_back_target and write_back_target not in SAMPLE_WRITE_BACK_COLUMNS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"write_back_target '{write_back_target}' not allowed; "
                    f"allowed: {sorted(SAMPLE_WRITE_BACK_COLUMNS)}"
                ),
            )
        self.repo.add_field_link(
            entry_id=entry_id,
            field_definition_id=field_definition_id,
            sort_order=sort_order,
            visible=visible,
            write_back_target=write_back_target,
        )

    def update_entry(self, entry_id: UUID, data: EntryUpdate) -> Entry:
        entry = self.get_entry(entry_id)
        kwargs: Dict[str, Any] = {"modified_by": self._user_id()}
        for field in (
            "name",
            "description",
            "active",
            "sort_order",
            "config",
            "process_step_id",
        ):
            val = getattr(data, field)
            if val is not None:
                if (
                    field == "config"
                    and entry.predefined_entry_key == "aliquot_pool_plan"
                ):
                    next_config = dict(val)
                    method_raw = next_config.get(
                        "method",
                        (entry.config or {}).get(
                            "method",
                            AliquotMethod.aliquot_by_volume.value,
                        ),
                    )
                    try:
                        AliquotMethod(method_raw)
                    except ValueError as exc:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "code": "invalid_aliquot_method",
                                "message": (
                                    f"Unknown concrete aliquot/pool method: {method_raw}"
                                ),
                            },
                        ) from exc
                    current_method = (entry.config or {}).get(
                        "method",
                        AliquotMethod.aliquot_by_volume.value,
                    )
                    if (entry.config or {}).get(
                        "plan_lines"
                    ) and method_raw != current_method:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail={
                                "code": "method_change_requires_cancel",
                                "message": (
                                    "Method cannot change after plan lines exist. "
                                    "Cancel the experiment and create a new plan; "
                                    "minted daughters are not removed."
                                ),
                            },
                        )
                kwargs[field] = val
        self.repo.update_entry(entry, **kwargs)
        self._commit_refresh(entry)
        return self.get_entry(entry_id)

    def delete_entry(self, entry_id: UUID) -> None:
        entry = self.get_entry(entry_id)
        self.repo.soft_delete_entry(entry)
        entry.modified_by = self._user_id()
        self._commit_refresh(entry)

    def instantiate_from_template(
        self,
        experiment_id: UUID,
        data: Optional[InstantiateEntriesRequest] = None,
    ) -> List[Entry]:
        """Create entries from template_definition['entries'] on the experiment's template."""
        data = data or InstantiateEntriesRequest()
        experiment = self.repo.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found",
            )
        if data.skip_if_exists and self.repo.count_for_experiment(experiment_id) > 0:
            return self.repo.list_for_experiment(
                experiment_id, active=None, load_values=False
            )

        if not experiment.experiment_template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Experiment has no template; cannot instantiate entries",
            )
        template = experiment.experiment_template or self.repo.get_template(
            experiment.experiment_template_id
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Experiment template not found",
            )
        decls = (template.template_definition or {}).get("entries") or []
        if not isinstance(decls, list) or not decls:
            # No declarations — nothing to create
            return []

        created: List[Entry] = []
        for i, raw in enumerate(decls):
            if not isinstance(raw, dict):
                continue
            predef_key = raw.get("predefined_entry_key")
            defaults = PREDEFINED_ENTRY_DEFAULTS.get(predef_key) if predef_key else None
            entry_type = (
                raw.get("entry_type")
                or (defaults or {}).get("entry_type")
                or "experiment_data"
            )
            if entry_type not in ENTRY_TYPES:
                continue
            entry_type = normalize_entry_type(entry_type)
            name = raw.get("name") or (defaults or {}).get("name") or f"Entry {i + 1}"
            fields = raw.get("fields") or []
            config = dict((defaults or {}).get("config") or {})
            config.update(raw.get("config") or {})
            config.setdefault("status", "draft")
            # Template-level depends_on → instance config (names or predefined keys)
            deps = raw.get("depends_on")
            if deps is None:
                deps = (raw.get("config") or {}).get("depends_on")
            if deps:
                config["depends_on"] = list(deps) if isinstance(deps, list) else [deps]
            description = raw.get("description")
            if description is None and defaults:
                description = defaults.get("description")
            # Prefer columns[] sample_field keys into config for grid RO fields
            columns = raw.get("columns") or []
            sample_field_keys = [
                c.get("key")
                for c in columns
                if isinstance(c, dict)
                and c.get("kind") == "sample_field"
                and c.get("key")
            ]
            if sample_field_keys:
                config["sample_columns"] = sample_field_keys
            entry = self.repo.create_entry(
                experiment_id=experiment_id,
                entry_type=entry_type,
                name=name,
                description=description,
                predefined_entry_key=predef_key,
                sort_order=int(raw.get("sort_order", i)),
                config=config,
                process_step_id=data.process_step_id,
                created_by=self._user_id(),
                modified_by=self._user_id(),
            )
            # Also accept columns[] with field_definition kind
            for j, c in enumerate(columns):
                if not isinstance(c, dict) or c.get("kind") != "field_definition":
                    continue
                if not c.get("field_definition_id"):
                    continue
                try:
                    fid = UUID(str(c["field_definition_id"]))
                except (ValueError, TypeError):
                    continue
                wb = c.get("write_back_target")
                if wb and wb not in SAMPLE_WRITE_BACK_COLUMNS:
                    wb = None
                if self.repo.field_definition_exists(fid):
                    self.repo.add_field_link(
                        entry_id=entry.id,
                        field_definition_id=fid,
                        sort_order=int(c.get("sort_order", j)),
                        visible=bool(c.get("visible", True)),
                        write_back_target=wb,
                    )
            for j, f in enumerate(fields):
                if not isinstance(f, dict) or not f.get("field_definition_id"):
                    continue
                try:
                    fid = UUID(str(f["field_definition_id"]))
                except (ValueError, TypeError):
                    continue
                wb = f.get("write_back_target")
                if wb and wb not in SAMPLE_WRITE_BACK_COLUMNS:
                    wb = None
                if self.repo.field_definition_exists(fid):
                    self.repo.add_field_link(
                        entry_id=entry.id,
                        field_definition_id=fid,
                        sort_order=int(f.get("sort_order", j)),
                        visible=bool(f.get("visible", True)),
                        write_back_target=wb,
                    )
            created.append(entry)

        if self.auto_commit:
            self.db.commit()
        return [self.get_entry(e.id) for e in created]

    def delete_row(self, entry_id: UUID, row_key: str) -> int:
        """Remove all cells for one experiment_data table row."""
        entry = self.get_entry(entry_id)
        if not is_experiment_scoped_entry(entry.entry_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Row delete is only for experiment_data entries",
            )
        if not row_key or not str(row_key).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="row_key required"
            )
        n = self.repo.delete_values_for_row(entry_id, str(row_key).strip())
        if self.auto_commit:
            self.db.commit()
        return n

    def upsert_values(
        self,
        entry_id: UUID,
        values: List[EntryFieldValueUpsert],
        *,
        apply_write_back: Optional[bool] = None,
    ) -> List[EntryFieldValue]:
        """Save entry field values. Write-back only when apply_write_back=True (submit path)."""
        entry = self.get_entry(entry_id)
        if normalize_entry_type(entry.entry_type) in READ_ONLY_ENTRY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot write values to {entry.entry_type} entries",
            )
        status_cfg = (entry.config or {}).get("status") or "draft"
        if status_cfg == "submitted" and apply_write_back is not True:
            # Allow re-save after submit for free-edit-until-done; clear submitted → draft on edit
            cfg = dict(entry.config or {})
            cfg["status"] = "draft"
            self.repo.update_entry(entry, config=cfg, modified_by=self._user_id())

        # S6: cohort membership for any sample_id write / write-back
        cohort = set(self._experiment_sample_ids(entry.experiment_id))

        results: List[EntryFieldValue] = []
        for item in values:
            link = self.repo.get_field_link(entry_id, item.field_definition_id)
            if not link:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Field {item.field_definition_id} is not linked to this entry",
                )
            if is_sample_scoped_entry(entry.entry_type) and item.sample_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="sample_id is required for experiment_sample_data entry values",
                )
            # experiment_data multi-row tables use row_key; sample_id optional for purpose subset
            if (
                is_experiment_scoped_entry(entry.entry_type)
                and not item.row_key
                and not item.sample_id
            ):
                # Allow legacy single-cell (both null) or require row_key for multi-row
                pass
            if (
                is_experiment_scoped_entry(entry.entry_type)
                and item.row_key
                and item.sample_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="experiment_data row_key values cannot also set sample_id",
                )

            if item.sample_id is not None:
                self._assert_sample_in_cohort(
                    item.sample_id, cohort, entry.experiment_id
                )

            value_kwargs = {
                "value_text": item.value_text,
                "value_number": item.value_number,
                "value_list_entry_id": item.value_list_entry_id,
                "value_date": item.value_date,
                "value_boolean": item.value_boolean,
                "value_json": item.value_json,
                "modified_by": self._user_id(),
            }
            existing = self.repo.get_value(
                entry_id,
                item.field_definition_id,
                item.sample_id,
                row_key=item.row_key,
            )
            if existing:
                val = self.repo.update_value(existing, **value_kwargs)
            else:
                val = self.repo.create_value(
                    entry_id=entry_id,
                    field_definition_id=item.field_definition_id,
                    sample_id=item.sample_id,
                    row_key=item.row_key,
                    created_by=self._user_id(),
                    **{k: v for k, v in value_kwargs.items() if k != "modified_by"},
                    modified_by=self._user_id(),
                )

            do_wb = (
                apply_write_back
                if apply_write_back is not None
                else item.apply_write_back
            )
            if do_wb and link.write_back_target and item.sample_id:
                self._apply_write_back(
                    val, item.sample_id, link.write_back_target, item, cohort=cohort
                )

            results.append(val)

        if self.auto_commit:
            self.db.commit()
            for v in results:
                try:
                    self.db.refresh(v)
                except Exception:
                    pass
        return results

    def submit_entry(self, entry_id: UUID) -> Tuple[Entry, int]:
        """Mark entry submitted and apply write-back for mapped sample-scoped values."""
        entry = self.get_entry(entry_id)
        if normalize_entry_type(entry.entry_type) in READ_ONLY_ENTRY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot submit read-only entry type",
            )
        # Template entry dependencies: depends_on names / predefined keys must be submitted first
        self._assert_dependencies_met(entry)
        cohort = set(self._experiment_sample_ids(entry.experiment_id))
        write_backs = 0
        values = self.repo.list_values(entry_id)
        for val in values:
            link = self.repo.get_field_link(entry_id, val.field_definition_id)
            if not link or not link.write_back_target:
                continue
            if not val.sample_id:
                continue
            if link.write_back_target not in SAMPLE_WRITE_BACK_COLUMNS:
                continue
            item = EntryFieldValueUpsert(
                field_definition_id=val.field_definition_id,
                sample_id=val.sample_id,
                value_text=val.value_text,
                value_number=(
                    float(val.value_number) if val.value_number is not None else None
                ),
                value_list_entry_id=val.value_list_entry_id,
                value_date=val.value_date,
                value_boolean=val.value_boolean,
                value_json=val.value_json,
                apply_write_back=True,
            )
            self._apply_write_back(
                val, val.sample_id, link.write_back_target, item, cohort=cohort
            )
            write_backs += 1

        cfg = dict(entry.config or {})
        cfg["status"] = "submitted"
        cfg["submitted_at"] = datetime.now(timezone.utc).isoformat()
        self.repo.update_entry(entry, config=cfg, modified_by=self._user_id())
        self._commit_refresh(entry)
        return self.get_entry(entry_id), write_backs

    def _assert_dependencies_met(self, entry: Entry) -> None:
        """
        Gate submit when config.depends_on lists other entry names or predefined keys.
        Example: depends_on: ["Experiment header"] or ["experiment_header"].
        """
        deps = (entry.config or {}).get("depends_on") or []
        if not deps:
            return
        siblings = self.repo.list_for_experiment(
            entry.experiment_id, active=True, load_values=False
        )
        by_name = {e.name: e for e in siblings}
        by_key = {e.predefined_entry_key: e for e in siblings if e.predefined_entry_key}
        missing: List[str] = []
        for dep in deps:
            if not isinstance(dep, str) or not dep.strip():
                continue
            target = by_key.get(dep) or by_name.get(dep)
            if not target:
                missing.append(f"{dep} (not found)")
                continue
            if target.id == entry.id:
                continue
            status_cfg = (target.config or {}).get("status") or "draft"
            if status_cfg != "submitted":
                missing.append(target.name or dep)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "dependencies_not_met",
                    "message": "Submit required predecessor entries first",
                    "missing": missing,
                },
            )

    def get_grid(self, entry_id: UUID) -> EntryGridResponse:
        entry = self.get_entry(entry_id)
        entry_type = normalize_entry_type(entry.entry_type)
        columns = self._grid_columns(entry)
        rows: List[EntryGridRow] = []
        empty_reason = None
        row_policy = "manual"

        if is_sample_scoped_entry(entry.entry_type):
            row_policy = "experiment_samples"
            if entry.predefined_entry_key == "aliquots_pools":
                sample_ids = [
                    UUID(str(sample_id))
                    for sample_id in (entry.config or {}).get(
                        "minted_sample_ids",
                        [],
                    )
                ]
                row_policy = "execute_minted_samples"
            else:
                sample_ids = self._experiment_sample_ids(entry.experiment_id)
            if not sample_ids:
                empty_reason = "no_samples_on_experiment"
            samples = self._load_samples(sample_ids)
            values = self.repo.list_values(entry_id)
            by_sample_field: Dict[Tuple[Optional[UUID], UUID], EntryFieldValue] = {
                (v.sample_id, v.field_definition_id): v for v in values
            }
            for sid in sample_ids:
                sample = samples.get(sid)
                cells: Dict[str, EntryGridCell] = {}
                for col in columns:
                    if col.kind == "sample_field":
                        cells[col.key] = self._sample_field_cell(sample, col.key)
                    elif col.field_definition_id:
                        v = by_sample_field.get((sid, col.field_definition_id))
                        cells[col.key] = self._value_to_cell(v, col.data_type)
                rows.append(
                    EntryGridRow(
                        row_id=str(sid),
                        sample_id=sid,
                        cells=cells,
                    )
                )
        else:
            # experiment_data: multi-row table keyed by row_key (preferred)
            # or legacy: one row per sample_id / single null row
            values = self.repo.list_values(entry_id)
            row_keys = sorted({v.row_key for v in values if v.row_key})
            by_row_field: Dict[Tuple[Optional[str], UUID], EntryFieldValue] = {
                (v.row_key, v.field_definition_id): v for v in values if v.row_key
            }
            if row_keys:
                for rk in row_keys:
                    cells = {}
                    for col in columns:
                        if col.field_definition_id:
                            v = by_row_field.get((rk, col.field_definition_id))
                            cells[col.key] = self._value_to_cell(v, col.data_type)
                    rows.append(EntryGridRow(row_id=rk, sample_id=None, cells=cells))
            else:
                sample_ids_present = sorted(
                    {v.sample_id for v in values if v.sample_id is not None},
                    key=lambda x: str(x),
                )
                by_key: Dict[Tuple[Optional[UUID], UUID], EntryFieldValue] = {
                    (v.sample_id, v.field_definition_id): v
                    for v in values
                    if not v.row_key
                }
                if sample_ids_present:
                    for sid in sample_ids_present:
                        cells = {}
                        for col in columns:
                            if col.field_definition_id:
                                v = by_key.get((sid, col.field_definition_id))
                                cells[col.key] = self._value_to_cell(v, col.data_type)
                        rows.append(
                            EntryGridRow(row_id=str(sid), sample_id=sid, cells=cells)
                        )
                else:
                    cells = {}
                    for col in columns:
                        if col.field_definition_id:
                            v = by_key.get((None, col.field_definition_id))
                            cells[col.key] = self._value_to_cell(v, col.data_type)
                    if columns:
                        rows.append(
                            EntryGridRow(
                                row_id="experiment", sample_id=None, cells=cells
                            )
                        )

        status_cfg = (entry.config or {}).get("status") or "draft"
        return EntryGridResponse(
            entry_id=entry.id,
            experiment_id=entry.experiment_id,
            entry_type=entry_type,
            name=entry.name,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            meta=EntryGridMeta(
                row_policy=row_policy,
                status=status_cfg,
                empty_reason=empty_reason,
            ),
        )

    def export_entry(self, entry_id: UUID) -> EntryExportResponse:
        entry = self.get_entry(entry_id)
        experiment = self.repo.get_experiment(entry.experiment_id)
        exp_name = getattr(experiment, "name", None) if experiment else None
        columns = self._grid_columns(entry)
        out: List[EntryExportRow] = []

        if is_sample_scoped_entry(entry.entry_type):
            if entry.predefined_entry_key == "aliquots_pools":
                sample_ids = [
                    UUID(str(sample_id))
                    for sample_id in (entry.config or {}).get(
                        "minted_sample_ids",
                        [],
                    )
                ]
            else:
                sample_ids = self._experiment_sample_ids(entry.experiment_id)
            samples = self._load_samples(sample_ids)
            values = self.repo.list_values(entry_id)
            by_sf: Dict[Tuple[Optional[UUID], UUID], EntryFieldValue] = {
                (v.sample_id, v.field_definition_id): v for v in values
            }
            for sid in sample_ids:
                sample = samples.get(sid)
                client_sid = (
                    getattr(sample, "client_sample_id", None) if sample else None
                )
                for col in columns:
                    if col.kind == "sample_field":
                        cell = self._sample_field_cell(sample, col.key)
                        out.append(
                            EntryExportRow(
                                experiment_id=entry.experiment_id,
                                experiment_name=exp_name,
                                entry_id=entry.id,
                                entry_name=entry.name,
                                entry_type=normalize_entry_type(entry.entry_type),
                                sample_id=sid,
                                client_sample_id=client_sid,
                                field_definition_id=None,
                                field_name=col.key,
                                field_display_name=col.label,
                                column_kind="sample_field",
                                data_type=col.data_type,
                                value_text=(
                                    str(cell.value)
                                    if cell.value is not None
                                    and col.data_type == "text"
                                    else None
                                ),
                                value_number=(
                                    cell.value if col.data_type == "number" else None
                                ),
                                value_date=(
                                    cell.value if col.data_type == "date" else None
                                ),
                                display_value=cell.display,
                            )
                        )
                    elif col.field_definition_id:
                        v = by_sf.get((sid, col.field_definition_id))
                        out.append(
                            self._export_from_value(
                                entry,
                                exp_name,
                                sid,
                                client_sid,
                                col,
                                v,
                            )
                        )
        else:
            values = self.repo.list_values(entry_id)
            by_key = {(v.sample_id, v.field_definition_id): v for v in values}
            sample_ids = sorted(
                {v.sample_id for v in values if v.sample_id},
                key=lambda x: str(x),
            ) or [None]
            for sid in sample_ids:
                for col in columns:
                    if not col.field_definition_id:
                        continue
                    v = by_key.get((sid, col.field_definition_id))
                    out.append(
                        self._export_from_value(entry, exp_name, sid, None, col, v)
                    )

        return EntryExportResponse(entry_id=entry.id, rows=out, total=len(out))

    def _grid_columns(self, entry: Entry) -> List[EntryGridColumn]:
        cols: List[EntryGridColumn] = []
        config = entry.config or {}
        sample_keys = config.get("sample_columns") or []
        # Default RO fields for sample-scoped entries if not configured
        if is_sample_scoped_entry(entry.entry_type) and not sample_keys:
            sample_keys = ["client_sample_id", "specimen_biotype_id", "received_date"]
        order = 0
        for key in sample_keys:
            meta = SAMPLE_SYSTEM_FIELDS.get(key)
            if not meta:
                continue
            cols.append(
                EntryGridColumn(
                    key=key,
                    kind="sample_field",
                    field_definition_id=None,
                    label=meta["label"],
                    data_type=meta["data_type"],
                    editable=False,
                    sort_order=order,
                )
            )
            order += 1
        links = sorted(
            entry.field_definition_links or [],
            key=lambda L: (L.sort_order, str(L.field_definition_id)),
        )
        for link in links:
            if link.visible is False:
                continue
            fd = self.repo.get_field_definition(link.field_definition_id)
            label = (
                (fd.display_name or fd.name) if fd else str(link.field_definition_id)
            )
            data_type = fd.data_type if fd else "text"
            cols.append(
                EntryGridColumn(
                    key=str(link.field_definition_id),
                    kind="field_definition",
                    field_definition_id=link.field_definition_id,
                    label=label,
                    data_type=data_type,
                    editable=True,
                    sort_order=(
                        order if link.sort_order is None else link.sort_order + 100
                    ),
                    write_back_target=link.write_back_target,
                )
            )
            order += 1
        cols.sort(key=lambda c: c.sort_order)
        return cols

    def _experiment_sample_ids(self, experiment_id: UUID) -> List[UUID]:
        rows = (
            self.db.query(ExperimentSampleExecution)
            .filter(ExperimentSampleExecution.experiment_id == experiment_id)
            .order_by(
                ExperimentSampleExecution.created_at,
                ExperimentSampleExecution.sample_id,
            )
            .all()
        )
        seen = set()
        ids: List[UUID] = []
        for r in rows:
            if r.sample_id and r.sample_id not in seen:
                seen.add(r.sample_id)
                ids.append(r.sample_id)
        return ids

    def _assert_sample_in_cohort(
        self,
        sample_id: UUID,
        cohort: set,
        experiment_id: UUID,
    ) -> None:
        """S6: sample_id must be on the experiment cohort."""
        if sample_id not in cohort:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "sample_not_in_cohort",
                    "message": (
                        f"sample_id {sample_id} is not in the experiment cohort "
                        f"({experiment_id})"
                    ),
                },
            )

    def _load_samples(self, sample_ids: List[UUID]) -> Dict[UUID, Sample]:
        if not sample_ids:
            return {}
        samples = self.db.query(Sample).filter(Sample.id.in_(sample_ids)).all()
        return {s.id: s for s in samples}

    def _sample_field_cell(self, sample: Optional[Sample], key: str) -> EntryGridCell:
        if (
            not sample
            or not hasattr(sample, key)
            and key
            not in (
                "sample_type",
                "status",
                "matrix",
                "specimen_biotype_id",
            )
        ):
            # FK fields may use different attr names
            pass
        meta = SAMPLE_SYSTEM_FIELDS.get(key) or {"data_type": "text"}
        raw = None
        if sample is not None:
            if key == "sample_type":
                raw = getattr(sample, "sample_type", None)
            elif key == "status":
                raw = getattr(sample, "status", None)
            elif key == "matrix":
                raw = getattr(sample, "matrix", None)
            elif hasattr(sample, key):
                raw = getattr(sample, key)
        display = None
        value = raw
        if meta["data_type"] == "list" and raw is not None:
            le = self.db.query(ListEntry).filter(ListEntry.id == raw).first()
            display = le.name if le else str(raw)
            value = str(raw)
        elif isinstance(raw, (datetime, date)):
            display = raw.isoformat() if hasattr(raw, "isoformat") else str(raw)
            value = display
        elif raw is not None:
            display = str(raw)
        return EntryGridCell(
            value=value,
            display=display,
            value_type=meta["data_type"],
        )

    def _value_to_cell(
        self, v: Optional[EntryFieldValue], data_type: str
    ) -> EntryGridCell:
        if not v:
            return EntryGridCell(value=None, display=None, value_type=data_type)
        if data_type in ("list", "lookup") and v.value_list_entry_id:
            le = (
                self.db.query(ListEntry)
                .filter(ListEntry.id == v.value_list_entry_id)
                .first()
            )
            return EntryGridCell(
                value=str(v.value_list_entry_id),
                display=le.name if le else str(v.value_list_entry_id),
                value_type=data_type,
                value_id=v.id,
            )
        if data_type == "number":
            num = float(v.value_number) if v.value_number is not None else None
            return EntryGridCell(
                value=num,
                display=str(num) if num is not None else None,
                value_type="number",
                value_id=v.id,
            )
        if data_type == "boolean":
            return EntryGridCell(
                value=v.value_boolean,
                display=str(v.value_boolean) if v.value_boolean is not None else None,
                value_type="boolean",
                value_id=v.id,
            )
        if data_type == "date":
            d = v.value_date
            disp = d.isoformat() if d is not None and hasattr(d, "isoformat") else None
            return EntryGridCell(
                value=disp, display=disp, value_type="date", value_id=v.id
            )
        if data_type == "json":
            return EntryGridCell(
                value=v.value_json,
                display=None,
                value_type="json",
                value_id=v.id,
            )
        return EntryGridCell(
            value=v.value_text,
            display=v.value_text,
            value_type="text",
            value_id=v.id,
        )

    def _export_from_value(
        self,
        entry: Entry,
        exp_name: Optional[str],
        sample_id: Optional[UUID],
        client_sample_id: Optional[str],
        col: EntryGridColumn,
        v: Optional[EntryFieldValue],
    ) -> EntryExportRow:
        cell = self._value_to_cell(v, col.data_type)
        return EntryExportRow(
            experiment_id=entry.experiment_id,
            experiment_name=exp_name,
            entry_id=entry.id,
            entry_name=entry.name,
            entry_type=normalize_entry_type(entry.entry_type),
            sample_id=sample_id,
            client_sample_id=client_sample_id,
            field_definition_id=col.field_definition_id,
            field_name=col.key,
            field_display_name=col.label,
            column_kind=col.kind,
            data_type=col.data_type,
            value_text=v.value_text if v else None,
            value_number=(
                float(v.value_number) if v and v.value_number is not None else None
            ),
            value_list_entry_id=v.value_list_entry_id if v else None,
            value_list_entry_name=(
                cell.display if col.data_type in ("list", "lookup") else None
            ),
            value_date=v.value_date if v else None,
            value_boolean=v.value_boolean if v else None,
            value_json=v.value_json if v else None,
            display_value=cell.display,
            modified_at=v.modified_at if v else None,
            modified_by=v.modified_by if v else None,
        )

    def _apply_write_back(
        self,
        value_row: EntryFieldValue,
        sample_id: UUID,
        target_column: str,
        item: EntryFieldValueUpsert,
        *,
        cohort: Optional[set] = None,
        experiment_id: Optional[UUID] = None,
    ) -> None:
        if target_column not in SAMPLE_WRITE_BACK_COLUMNS:
            return
        # S6: refuse write-back outside experiment cohort
        if cohort is not None:
            exp_id = experiment_id
            if exp_id is None:
                entry = (
                    self.db.query(Entry).filter(Entry.id == value_row.entry_id).first()
                )
                exp_id = entry.experiment_id if entry else None
            if exp_id is not None:
                self._assert_sample_in_cohort(sample_id, cohort, exp_id)
        sample = self.db.query(Sample).filter(Sample.id == sample_id).first()
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sample {sample_id} not found for write-back",
            )
        if not hasattr(sample, target_column):
            return

        previous = getattr(sample, target_column)
        new_val = self._coerce_write_back_value(target_column, item)
        setattr(sample, target_column, new_val)

        prev_serializable = previous
        if isinstance(previous, (datetime, Decimal)):
            prev_serializable = str(previous)
        elif previous is not None and not isinstance(
            previous, (str, int, float, bool, dict, list)
        ):
            prev_serializable = str(previous)

        self.repo.update_value(
            value_row,
            write_back_at=datetime.now(timezone.utc),
            write_back_previous={"column": target_column, "value": prev_serializable},
            modified_by=self._user_id(),
        )
        self.db.flush()

    def _coerce_write_back_value(self, column: str, item: EntryFieldValueUpsert) -> Any:
        if column.endswith("_id") or column in ("specimen_biotype_id",):
            return item.value_list_entry_id
        if column in ("temperature",):
            return item.value_number
        if column in ("date_sampled", "received_date", "due_date", "report_date"):
            return item.value_date
        # Prefer list entry, then text, then number
        if item.value_list_entry_id is not None:
            return item.value_list_entry_id
        if item.value_text is not None:
            return item.value_text
        if item.value_number is not None:
            return item.value_number
        if item.value_boolean is not None:
            return item.value_boolean
        return item.value_date
