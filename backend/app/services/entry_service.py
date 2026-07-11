"""
Service for Experiment Entries (Phase 2).

Template declaration lives in:
  ExperimentTemplate.template_definition['entries']  # list of entry defs

Write-back policy (Phase 2):
  - Only SAMPLE_WRITE_BACK_COLUMNS allowlist
  - Last write wins
  - Previous sample value stored on EntryFieldValue.write_back_previous
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.entry_repository import EntryRepository
from app.schemas.entry import (
    EntryCreate,
    EntryUpdate,
    EntryFieldValueUpsert,
    InstantiateEntriesRequest,
)
from models.entry import (
    Entry,
    EntryFieldValue,
    ENTRY_TYPES,
    SAMPLE_WRITE_BACK_COLUMNS,
)
from models.sample import Sample
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
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
        if not self.repo.get_experiment(data.experiment_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found",
            )
        entry = self.repo.create_entry(
            experiment_id=data.experiment_id,
            entry_type=data.entry_type,
            name=data.name,
            description=data.description,
            predefined_entry_key=data.predefined_entry_key,
            sort_order=data.sort_order or 0,
            config=data.config,
            process_step_id=data.process_step_id,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        if data.fields:
            for f in data.fields:
                self._add_field_link(entry.id, f.field_definition_id, f.sort_order or 0, f.visible, f.write_back_target)
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
        kwargs: Dict[str, Any] = {'modified_by': self._user_id()}
        for field in ('name', 'description', 'active', 'sort_order', 'config', 'process_step_id'):
            val = getattr(data, field)
            if val is not None:
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
            return self.repo.list_for_experiment(experiment_id, active=None, load_values=False)

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
        decls = (template.template_definition or {}).get('entries') or []
        if not isinstance(decls, list) or not decls:
            # No declarations — nothing to create
            return []

        created: List[Entry] = []
        for i, raw in enumerate(decls):
            if not isinstance(raw, dict):
                continue
            entry_type = raw.get('entry_type') or 'experiment_detail'
            if entry_type not in ENTRY_TYPES:
                continue
            name = raw.get('name') or f'Entry {i + 1}'
            fields = raw.get('fields') or []
            entry = self.repo.create_entry(
                experiment_id=experiment_id,
                entry_type=entry_type,
                name=name,
                description=raw.get('description'),
                predefined_entry_key=raw.get('predefined_entry_key'),
                sort_order=int(raw.get('sort_order', i)),
                config=raw.get('config') or {},
                process_step_id=data.process_step_id,
                created_by=self._user_id(),
                modified_by=self._user_id(),
            )
            for j, f in enumerate(fields):
                if not isinstance(f, dict) or not f.get('field_definition_id'):
                    continue
                try:
                    fid = UUID(str(f['field_definition_id']))
                except (ValueError, TypeError):
                    continue
                wb = f.get('write_back_target')
                if wb and wb not in SAMPLE_WRITE_BACK_COLUMNS:
                    wb = None
                if self.repo.field_definition_exists(fid):
                    self.repo.add_field_link(
                        entry_id=entry.id,
                        field_definition_id=fid,
                        sort_order=int(f.get('sort_order', j)),
                        visible=bool(f.get('visible', True)),
                        write_back_target=wb,
                    )
            created.append(entry)

        if self.auto_commit:
            self.db.commit()
        return [self.get_entry(e.id) for e in created]

    def upsert_values(
        self,
        entry_id: UUID,
        values: List[EntryFieldValueUpsert],
    ) -> List[EntryFieldValue]:
        entry = self.get_entry(entry_id)
        if entry.entry_type == 'display_table':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot write values to display_table entries",
            )
        results: List[EntryFieldValue] = []
        for item in values:
            link = self.repo.get_field_link(entry_id, item.field_definition_id)
            if not link:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Field {item.field_definition_id} is not linked to this entry",
                )
            if entry.entry_type == 'sample_data' and item.sample_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="sample_id is required for sample_data entry values",
                )
            if entry.entry_type == 'experiment_detail' and item.sample_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="sample_id must be null for experiment_detail entry values",
                )

            value_kwargs = {
                'value_text': item.value_text,
                'value_number': item.value_number,
                'value_list_entry_id': item.value_list_entry_id,
                'value_date': item.value_date,
                'value_boolean': item.value_boolean,
                'value_json': item.value_json,
                'modified_by': self._user_id(),
            }
            existing = self.repo.get_value(
                entry_id,
                item.field_definition_id,
                item.sample_id,
            )
            if existing:
                val = self.repo.update_value(existing, **value_kwargs)
            else:
                val = self.repo.create_value(
                    entry_id=entry_id,
                    field_definition_id=item.field_definition_id,
                    sample_id=item.sample_id,
                    created_by=self._user_id(),
                    **{k: v for k, v in value_kwargs.items() if k != 'modified_by'},
                    modified_by=self._user_id(),
                )

            if item.apply_write_back and link.write_back_target and item.sample_id:
                self._apply_write_back(val, item.sample_id, link.write_back_target, item)

            results.append(val)

        if self.auto_commit:
            self.db.commit()
            for v in results:
                try:
                    self.db.refresh(v)
                except Exception:
                    pass
        return results

    def _apply_write_back(
        self,
        value_row: EntryFieldValue,
        sample_id: UUID,
        target_column: str,
        item: EntryFieldValueUpsert,
    ) -> None:
        if target_column not in SAMPLE_WRITE_BACK_COLUMNS:
            return
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
        elif previous is not None and not isinstance(previous, (str, int, float, bool, dict, list)):
            prev_serializable = str(previous)

        self.repo.update_value(
            value_row,
            write_back_at=datetime.now(timezone.utc),
            write_back_previous={'column': target_column, 'value': prev_serializable},
            modified_by=self._user_id(),
        )
        self.db.flush()

    def _coerce_write_back_value(self, column: str, item: EntryFieldValueUpsert) -> Any:
        if column.endswith('_id') or column in ('specimen_biotype_id',):
            return item.value_list_entry_id
        if column in ('temperature',):
            return item.value_number
        if column in ('date_sampled', 'received_date', 'due_date', 'report_date'):
            return item.value_date
        if column == 'client_sample_id':
            return item.value_text
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
