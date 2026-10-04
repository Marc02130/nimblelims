"""Named lab configuration, its file chunks, runs, and the ledger of what was stored."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from .base import Base

SETTINGS_ID = uuid.UUID("c0a16ae0-0000-4000-8000-000000000001")
EMBEDDING_DIM = 384


class ConfiguringAgentSettings(Base):
    __tablename__ = "configuring_agent_settings"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    agent_provider = Column(String(32))
    agent_model = Column(String(255))
    key_ciphertext = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))


class Configuration(Base):
    """A named configuration. File chunks and the ledger belong to this row, not to the user."""

    __tablename__ = "configurations"
    __table_args__ = (UniqueConstraint("client_id", "name", name="configurations_client_name_uniq"),)

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(PostgresUUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))

    documents = relationship("ConfigurationDocument", back_populates="configuration")
    items = relationship("ConfigurationItem", back_populates="configuration")
    runs = relationship("ConfigurationRun", back_populates="configuration")


class ConfigurationDocument(Base):
    __tablename__ = "configuration_documents"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    configuration_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("configurations.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    file_type = Column(String(16), nullable=False)
    content = Column(Text)
    status = Column(String(16), nullable=False, default="processing")
    embedding_model = Column(String(128))
    chunk_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))

    configuration = relationship("Configuration", back_populates="documents")
    chunks = relationship("ConfigurationChunk", back_populates="document")


class ConfigurationChunk(Base):
    __tablename__ = "configuration_chunks"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    configuration_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("configurations.id", ondelete="CASCADE"), nullable=False
    )
    document_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("configuration_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    embedding_model = Column(String(128), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    heading = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("ConfigurationDocument", back_populates="chunks")


class ConfigurationRun(Base):
    __tablename__ = "configuration_runs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    configuration_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("configurations.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False)
    goal_note = Column(Text)
    banner = Column(Text)
    error_message = Column(Text)
    applied_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    stopped_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))

    configuration = relationship("Configuration", back_populates="runs")
    steps = relationship(
        "ConfigurationStep",
        back_populates="run",
        order_by="ConfigurationStep.position",
    )


class ConfigurationStep(Base):
    __tablename__ = "configuration_steps"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("configuration_runs.id", ondelete="CASCADE"), nullable=False
    )
    position = Column(Integer, nullable=False)
    group_name = Column(String(32), nullable=False)
    target = Column(String(255), nullable=False)
    action = Column(String(500), nullable=False)
    why = Column(String(500), nullable=False)
    decision = Column(String(16), nullable=False, default="pending")
    status = Column(String(16), nullable=False)
    call_method = Column(String(8))
    call_path = Column(Text)
    call_body = Column(JSONB)
    gap = Column(Text)
    error_message = Column(Text)

    run = relationship("ConfigurationRun", back_populates="steps")


class ConfigurationItem(Base):
    """One stored configuration object produced by a successful apply."""

    __tablename__ = "configuration_items"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    configuration_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("configurations.id", ondelete="CASCADE"), nullable=False
    )
    run_id = Column(PostgresUUID(as_uuid=True), ForeignKey("configuration_runs.id"))
    kind = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    target_id = Column(PostgresUUID(as_uuid=True))
    detail = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))

    configuration = relationship("Configuration", back_populates="items")
