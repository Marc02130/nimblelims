"""Data parser catalog: versioned CRUD, activate, setup files, test suite."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.schemas.data_parser import (
    DataParserCreate,
    DataParserNewVersion,
    DataParserRead,
    FileTestReport,
    ParserAnalysisLink,
    SetupFileMeta,
    TestSuiteResponse,
)
from app.schemas.flexible_experiment import ParserConfig
from app.services.instrument_data_service import ParserEngine
from models.analysis import Analysis
from models.flexible_experiment import DataParser, ParserAnalysis, ParserSetupFile
from models.instrument import CroSource, Instrument
from models.user import User

MAX_SETUP_FILES = 10
MAX_SETUP_FILE_BYTES = 10 * 1024 * 1024


class DataParserService:
    def __init__(self, db: Session, current_user: Optional[User] = None) -> None:
        self.db = db
        self.current_user = current_user

    def _user_id(self) -> Optional[uuid.UUID]:
        return self.current_user.id if self.current_user else None

    def _validate_config(self, config: ParserConfig | dict) -> dict:
        if isinstance(config, ParserConfig):
            return config.model_dump()
        return ParserConfig.model_validate(config).model_dump()

    def _to_read(self, p: DataParser) -> DataParserRead:
        links = [
            ParserAnalysisLink(analysis_id=l.analysis_id, is_default=l.is_default)
            for l in (p.analyses_links or [])
        ]
        return DataParserRead(
            id=p.id,
            name=p.name,
            description=p.description,
            instrument_id=p.instrument_id,
            cro_source_id=p.cro_source_id,
            version_group_id=p.version_group_id,
            version=p.version,
            active=p.active,
            parser_config=p.parser_config or {},
            analysis_ids=[l.analysis_id for l in links],
            analyses=links,
            instrument_name=p.instrument.name if p.instrument else None,
            cro_source_name=p.cro_source.name if p.cro_source else None,
            created_at=p.created_at,
            modified_at=p.modified_at,
        )

    def _require_source(self, instrument_id, cro_source_id) -> None:
        if instrument_id:
            if not self.db.query(Instrument).filter(Instrument.id == instrument_id).first():
                raise HTTPException(400, "Invalid instrument_id")
        if cro_source_id:
            if not self.db.query(CroSource).filter(CroSource.id == cro_source_id).first():
                raise HTTPException(400, "Invalid cro_source_id")

    def _require_analyses(self, links: List[ParserAnalysisLink]) -> None:
        for link in links:
            a = (
                self.db.query(Analysis)
                .filter(Analysis.id == link.analysis_id, Analysis.active.is_(True))
                .first()
            )
            if not a:
                raise HTTPException(400, f"Analysis {link.analysis_id} not found or inactive")

    def list_parsers(
        self,
        *,
        active_only: bool = True,
        instrument_id: Optional[uuid.UUID] = None,
        cro_source_id: Optional[uuid.UUID] = None,
        analysis_id: Optional[uuid.UUID] = None,
        version_group_id: Optional[uuid.UUID] = None,
    ) -> List[DataParserRead]:
        q = self.db.query(DataParser).options(
            joinedload(DataParser.analyses_links),
            joinedload(DataParser.instrument),
            joinedload(DataParser.cro_source),
        )
        if active_only:
            q = q.filter(DataParser.active.is_(True))
        if instrument_id:
            q = q.filter(DataParser.instrument_id == instrument_id)
        if cro_source_id:
            q = q.filter(DataParser.cro_source_id == cro_source_id)
        if version_group_id:
            q = q.filter(DataParser.version_group_id == version_group_id)
        if analysis_id:
            q = q.join(ParserAnalysis).filter(ParserAnalysis.analysis_id == analysis_id)
        rows = q.order_by(DataParser.name, DataParser.version.desc()).all()
        return [self._to_read(r) for r in rows]

    def get(self, parser_id: uuid.UUID) -> DataParser:
        p = (
            self.db.query(DataParser)
            .options(
                joinedload(DataParser.analyses_links),
                joinedload(DataParser.instrument),
                joinedload(DataParser.cro_source),
            )
            .filter(DataParser.id == parser_id)
            .first()
        )
        if not p:
            raise HTTPException(404, "Data parser not found")
        return p

    def create(self, body: DataParserCreate) -> DataParserRead:
        cfg = self._validate_config(body.parser_config)
        self._require_source(body.instrument_id, body.cro_source_id)
        self._require_analyses(body.analyses)

        parser_id = uuid.uuid4()
        group_id = parser_id
        p = DataParser(
            id=parser_id,
            name=body.name,
            description=body.description,
            instrument_id=body.instrument_id,
            cro_source_id=body.cro_source_id,
            version_group_id=group_id,
            version=1,
            active=False,
            parser_config=cfg,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        self.db.add(p)
        for link in body.analyses:
            self.db.add(
                ParserAnalysis(
                    parser_id=parser_id,
                    analysis_id=link.analysis_id,
                    is_default=link.is_default,
                )
            )
        self.db.flush()
        if body.activate:
            self._activate(p)
        self.db.commit()
        return self._to_read(self.get(parser_id))

    def create_version(
        self, version_group_id: uuid.UUID, body: DataParserNewVersion
    ) -> DataParserRead:
        existing = (
            self.db.query(DataParser)
            .filter(DataParser.version_group_id == version_group_id)
            .order_by(DataParser.version.desc())
            .first()
        )
        if not existing:
            raise HTTPException(404, "Version group not found")

        cfg = self._validate_config(body.parser_config)
        self._require_analyses(body.analyses)
        max_v = (
            self.db.query(func.max(DataParser.version))
            .filter(DataParser.version_group_id == version_group_id)
            .scalar()
            or 0
        )
        new_id = uuid.uuid4()
        p = DataParser(
            id=new_id,
            name=body.name or existing.name,
            description=body.description if body.description is not None else existing.description,
            instrument_id=existing.instrument_id,
            cro_source_id=existing.cro_source_id,
            version_group_id=version_group_id,
            version=max_v + 1,
            active=False,
            parser_config=cfg,
            created_by=self._user_id(),
            modified_by=self._user_id(),
        )
        self.db.add(p)
        for link in body.analyses:
            self.db.add(
                ParserAnalysis(
                    parser_id=new_id,
                    analysis_id=link.analysis_id,
                    is_default=link.is_default,
                )
            )
        self.db.flush()
        if body.activate:
            self._activate(p)
        self.db.commit()
        return self._to_read(self.get(new_id))

    def _activate(self, parser: DataParser) -> None:
        (
            self.db.query(DataParser)
            .filter(
                DataParser.version_group_id == parser.version_group_id,
                DataParser.id != parser.id,
            )
            .update({DataParser.active: False}, synchronize_session=False)
        )
        parser.active = True
        parser.modified_by = self._user_id()

    def activate(self, parser_id: uuid.UUID) -> DataParserRead:
        p = self.get(parser_id)
        self._activate(p)
        self.db.commit()
        return self._to_read(self.get(parser_id))

    def add_setup_file(
        self,
        *,
        parser_id: Optional[uuid.UUID],
        role: str,
        filename: str,
        content_type: Optional[str],
        content: bytes,
    ) -> SetupFileMeta:
        if role not in ("example", "test", "edge_fixture"):
            raise HTTPException(400, "Invalid role")
        if len(content) > MAX_SETUP_FILE_BYTES:
            raise HTTPException(400, f"File exceeds {MAX_SETUP_FILE_BYTES} bytes")
        if parser_id:
            self.get(parser_id)
            count = (
                self.db.query(ParserSetupFile)
                .filter(ParserSetupFile.parser_id == parser_id)
                .count()
            )
            if count >= MAX_SETUP_FILES:
                raise HTTPException(400, f"Max {MAX_SETUP_FILES} setup files per parser")

        f = ParserSetupFile(
            id=uuid.uuid4(),
            parser_id=parser_id,
            role=role,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            content=content,
            created_by=self._user_id(),
        )
        self.db.add(f)
        self.db.commit()
        self.db.refresh(f)
        return SetupFileMeta.model_validate(f)

    def list_setup_files(self, parser_id: uuid.UUID) -> List[SetupFileMeta]:
        self.get(parser_id)
        rows = (
            self.db.query(ParserSetupFile)
            .filter(ParserSetupFile.parser_id == parser_id)
            .order_by(ParserSetupFile.created_at)
            .all()
        )
        return [SetupFileMeta.model_validate(r) for r in rows]

    def test_config(
        self, config: ParserConfig | dict, files: list[tuple[str, bytes]]
    ) -> TestSuiteResponse:
        if len(files) > MAX_SETUP_FILES:
            raise HTTPException(400, f"Max {MAX_SETUP_FILES} files")
        for name, content in files:
            if len(content) > MAX_SETUP_FILE_BYTES:
                raise HTTPException(400, f"{name} exceeds size limit")
        cfg = self._validate_config(config)
        reports = ParserEngine().run_test_suite(cfg, files)
        file_reports = [
            FileTestReport(
                filename=r.filename,
                ok=r.ok,
                hard_errors=r.hard_errors,
                warnings=r.warnings,
                row_count=r.row_count,
            )
            for r in reports
        ]
        return TestSuiteResponse(
            all_clean=all(f.ok for f in file_reports) and len(file_reports) > 0,
            files=file_reports,
        )

    def resolve_for_import(
        self,
        *,
        analysis_id: uuid.UUID,
        instrument_id: Optional[uuid.UUID],
        cro_source_id: Optional[uuid.UUID],
        parser_id: Optional[uuid.UUID],
    ) -> DataParser:
        has_i = instrument_id is not None
        has_c = cro_source_id is not None
        if has_i == has_c:
            raise HTTPException(400, "Exactly one of instrument_id or cro_source_id required")

        if parser_id:
            p = self.get(parser_id)
            if not p.active:
                raise HTTPException(400, "Parser version is not active")
            if instrument_id and p.instrument_id != instrument_id:
                raise HTTPException(400, "Parser does not match instrument")
            if cro_source_id and p.cro_source_id != cro_source_id:
                raise HTTPException(400, "Parser does not match CRO source")
            linked = any(l.analysis_id == analysis_id for l in p.analyses_links)
            if not linked:
                raise HTTPException(400, "Parser is not linked to run analysis")
            return p

        q = (
            self.db.query(DataParser)
            .options(joinedload(DataParser.analyses_links))
            .join(ParserAnalysis)
            .filter(
                DataParser.active.is_(True),
                ParserAnalysis.analysis_id == analysis_id,
            )
        )
        if instrument_id:
            q = q.filter(DataParser.instrument_id == instrument_id)
        else:
            q = q.filter(DataParser.cro_source_id == cro_source_id)

        candidates = q.all()
        if not candidates:
            raise HTTPException(
                400,
                "No active data parser for this analysis and instrument/CRO",
            )
        # Prefer is_default for this analysis
        for p in candidates:
            for link in p.analyses_links:
                if link.analysis_id == analysis_id and link.is_default:
                    return p
        return candidates[0]
