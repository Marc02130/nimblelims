"""UI schema registries (not lab data). Physical CREATE/ALTER is real Postgres."""
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Identity, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base
import uuid


class SchemaTable(Base):
    __tablename__ = "schema_tables"
    __table_args__ = (
        UniqueConstraint("client_id", "physical_name", name="uq_schema_tables_client_physical"),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    display_name = Column(String(255), nullable=False)
    physical_name = Column(String(63), nullable=False)
    kind = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="active")
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))

    columns = relationship("SchemaColumn", back_populates="table")


class SchemaColumn(Base):
    __tablename__ = "schema_columns"
    __table_args__ = (
        UniqueConstraint("table_id", "physical_name", name="uq_schema_columns_table_physical"),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    table_id = Column(PostgresUUID(as_uuid=True), ForeignKey("schema_tables.id"), nullable=False)
    display_name = Column(String(255), nullable=False)
    physical_name = Column(String(63), nullable=False)
    data_type = Column(String(32), nullable=False)
    nullable = Column(Boolean, default=True, nullable=False)
    list_id = Column(PostgresUUID(as_uuid=True), ForeignKey("lists.id"), nullable=True)
    sop_hint = Column(String(32), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    status = Column(String(16), nullable=False, default="active")
    is_platform = Column(Boolean, default=False, nullable=False)
    is_identity = Column(Boolean, default=False, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))

    table = relationship("SchemaTable", back_populates="columns")


class SchemaLayout(Base):
    __tablename__ = "schema_layouts"
    __table_args__ = (
        UniqueConstraint("client_id", "role_id", "screen_key", name="uq_schema_layouts_role_screen"),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    role_id = Column(PostgresUUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    screen_key = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))

    fields = relationship("SchemaLayoutField", back_populates="layout", cascade="all, delete-orphan")


class SchemaLayoutField(Base):
    __tablename__ = "schema_layout_fields"
    __table_args__ = (
        UniqueConstraint("layout_id", "column_id", name="uq_schema_layout_fields_membership"),
    )

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    layout_id = Column(PostgresUUID(as_uuid=True), ForeignKey("schema_layouts.id"), nullable=False)
    column_id = Column(PostgresUUID(as_uuid=True), ForeignKey("schema_columns.id"), nullable=False)
    section = Column(String(128), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)

    layout = relationship("SchemaLayout", back_populates="fields")
    column = relationship("SchemaColumn")


class SchemaPrivilege(Base):
    __tablename__ = "schema_privileges"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    role_id = Column(PostgresUUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    table_id = Column(PostgresUUID(as_uuid=True), ForeignKey("schema_tables.id"), nullable=False)
    column_id = Column(PostgresUUID(as_uuid=True), ForeignKey("schema_columns.id"), nullable=True)
    access = Column(String(16), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))


class SchemaChange(Base):
    __tablename__ = "schema_changes"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    actor_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    op = Column(String(32), nullable=False)
    table_physical = Column(String(63), nullable=False)
    column_physical = Column(String(63), nullable=True)
    before_status = Column(String(32), nullable=True)
    after_status = Column(String(32), nullable=True)
    definition_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class UiSchemaDdlLog(Base):
    __tablename__ = "ui_schema_ddl_log"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seq = Column(BigInteger, Identity(always=False), nullable=False)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    change_id = Column(PostgresUUID(as_uuid=True), ForeignKey("schema_changes.id"), nullable=True)
    op = Column(String(32), nullable=False)
    table_physical = Column(String(63), nullable=False)
    column_physical = Column(String(63), nullable=True)
    pg_type = Column(String(32), nullable=True)
    nullable = Column(Boolean, nullable=True)
    list_fk = Column(Boolean, nullable=True)
    applied_at = Column(DateTime, default=func.now(), nullable=False)
