"""Instrument catalog (types + instances) and CRO export sources — data-parsers P0."""
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class InstrumentType(BaseModel):
    """Vendor/model class (what the instrument is)."""

    __tablename__ = 'instrument_types'

    vendor = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)

    instruments = relationship('Instrument', back_populates='instrument_type')


class Instrument(BaseModel):
    """Physical or named instance of an instrument type (lab nickname + serial)."""

    __tablename__ = 'instruments'

    instrument_type_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('instrument_types.id'),
        nullable=False,
    )
    serial_number = Column(String(255), nullable=True)

    instrument_type = relationship('InstrumentType', back_populates='instruments')


class CroSource(BaseModel):
    """External/CRO export-source catalog (file shape lineage)."""

    __tablename__ = 'cro_sources'

    client_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey('clients.id'),
        nullable=True,
    )

    client = relationship('Client', foreign_keys=[client_id])
