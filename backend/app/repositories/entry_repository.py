"""Repository for Experiment Entries."""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from models.entry import Entry, EntryFieldDefinition, EntryFieldValue
from models.field_definition import FieldDefinition
from models.experiment import Experiment, ExperimentTemplate


class EntryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_entry(
        self,
        entry_id: UUID,
        load_values: bool = True,
        load_fields: bool = True,
    ) -> Optional[Entry]:
        q = self.db.query(Entry).filter(Entry.id == entry_id)
        if load_fields:
            q = q.options(joinedload(Entry.field_definition_links))
        if load_values:
            q = q.options(joinedload(Entry.values))
        return q.first()

    def list_for_experiment(
        self,
        experiment_id: UUID,
        active: Optional[bool] = True,
        load_values: bool = False,
    ) -> List[Entry]:
        q = self.db.query(Entry).filter(Entry.experiment_id == experiment_id)
        if active is not None:
            q = q.filter(Entry.active == active)
        q = q.options(joinedload(Entry.field_definition_links))
        if load_values:
            q = q.options(joinedload(Entry.values))
        return q.order_by(Entry.sort_order, Entry.name).all()

    def count_for_experiment(self, experiment_id: UUID) -> int:
        return (
            self.db.query(Entry)
            .filter(Entry.experiment_id == experiment_id)
            .count()
        )

    def get_experiment(self, experiment_id: UUID) -> Optional[Experiment]:
        return (
            self.db.query(Experiment)
            .options(joinedload(Experiment.experiment_template))
            .filter(Experiment.id == experiment_id)
            .first()
        )

    def get_template(self, template_id: UUID) -> Optional[ExperimentTemplate]:
        return (
            self.db.query(ExperimentTemplate)
            .filter(ExperimentTemplate.id == template_id)
            .first()
        )

    def field_definition_exists(self, field_id: UUID) -> bool:
        return (
            self.db.query(FieldDefinition.id)
            .filter(FieldDefinition.id == field_id)
            .first()
            is not None
        )

    def get_field_definition(self, field_id: UUID) -> Optional[FieldDefinition]:
        return (
            self.db.query(FieldDefinition)
            .filter(FieldDefinition.id == field_id)
            .first()
        )

    def create_entry(
        self,
        experiment_id: UUID,
        entry_type: str,
        name: str,
        description: Optional[str] = None,
        predefined_entry_key: Optional[str] = None,
        sort_order: int = 0,
        config: Optional[dict] = None,
        process_step_id: Optional[UUID] = None,
        active: bool = True,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> Entry:
        e = Entry(
            experiment_id=experiment_id,
            entry_type=entry_type,
            name=name,
            description=description,
            predefined_entry_key=predefined_entry_key,
            sort_order=sort_order,
            config=config or {},
            process_step_id=process_step_id,
            active=active,
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(e)
        self.db.flush()
        return e

    def update_entry(self, entry: Entry, **kwargs) -> Entry:
        for k, v in kwargs.items():
            if hasattr(entry, k):
                setattr(entry, k, v)
        self.db.flush()
        return entry

    def soft_delete_entry(self, entry: Entry) -> None:
        entry.active = False
        self.db.flush()

    def add_field_link(
        self,
        entry_id: UUID,
        field_definition_id: UUID,
        sort_order: int = 0,
        visible: bool = True,
        write_back_target: Optional[str] = None,
    ) -> EntryFieldDefinition:
        link = EntryFieldDefinition(
            entry_id=entry_id,
            field_definition_id=field_definition_id,
            sort_order=sort_order,
            visible=visible,
            write_back_target=write_back_target,
        )
        self.db.add(link)
        self.db.flush()
        return link

    def get_field_link(
        self,
        entry_id: UUID,
        field_definition_id: UUID,
    ) -> Optional[EntryFieldDefinition]:
        return (
            self.db.query(EntryFieldDefinition)
            .filter(
                EntryFieldDefinition.entry_id == entry_id,
                EntryFieldDefinition.field_definition_id == field_definition_id,
            )
            .first()
        )

    def get_value(
        self,
        entry_id: UUID,
        field_definition_id: UUID,
        sample_id: Optional[UUID],
    ) -> Optional[EntryFieldValue]:
        q = self.db.query(EntryFieldValue).filter(
            EntryFieldValue.entry_id == entry_id,
            EntryFieldValue.field_definition_id == field_definition_id,
        )
        if sample_id is None:
            q = q.filter(EntryFieldValue.sample_id.is_(None))
        else:
            q = q.filter(EntryFieldValue.sample_id == sample_id)
        return q.first()

    def create_value(
        self,
        entry_id: UUID,
        field_definition_id: UUID,
        sample_id: Optional[UUID] = None,
        value_text: Optional[str] = None,
        value_number=None,
        value_list_entry_id: Optional[UUID] = None,
        value_date=None,
        value_boolean: Optional[bool] = None,
        value_json=None,
        created_by: Optional[UUID] = None,
        modified_by: Optional[UUID] = None,
    ) -> EntryFieldValue:
        v = EntryFieldValue(
            entry_id=entry_id,
            field_definition_id=field_definition_id,
            sample_id=sample_id,
            value_text=value_text,
            value_number=value_number,
            value_list_entry_id=value_list_entry_id,
            value_date=value_date,
            value_boolean=value_boolean,
            value_json=value_json,
            created_by=created_by,
            modified_by=modified_by,
        )
        self.db.add(v)
        self.db.flush()
        return v

    def update_value(self, value: EntryFieldValue, **kwargs) -> EntryFieldValue:
        for k, v in kwargs.items():
            if hasattr(value, k):
                setattr(value, k, v)
        self.db.flush()
        return value

    def list_values(
        self,
        entry_id: UUID,
        sample_id: Optional[UUID] = None,
    ) -> List[EntryFieldValue]:
        q = self.db.query(EntryFieldValue).filter(EntryFieldValue.entry_id == entry_id)
        if sample_id is not None:
            q = q.filter(EntryFieldValue.sample_id == sample_id)
        return q.all()
