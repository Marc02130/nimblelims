"""
SOPParseService — creates and manages SOP parse jobs.

Background task flow:
    1. POST /sop-parse: create job (status=pending), kick off background task
    2. Background task: set status=processing → call Claude API
    3. On success: set status=complete, store result JSONB
    4. On failure: set status=failed, store error_message
    5. GET /sop-parse/:id: poll status

Claude extraction prompt produces:
    {
      "template_definition": TemplateDefinition dict,
      "parser_config": ParserConfig dict,
      "worklist_config": WorklistConfig dict
    }

Background tasks use their own SessionLocal() to avoid sharing a session with the
HTTP request that spawned them (per design doc decision).
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

import anthropic
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import ANTHROPIC_API_KEY
from app.repositories.flexible_experiment_repository import (
    SopParseJobRepository,
    InstrumentParserRepository,
    RobotWorklistConfigRepository,
)
from models.experiment import ExperimentTemplate
from models.flexible_experiment import SopParseJob, SopParseJobStatus

# Structured extraction prompt for Claude
_EXTRACTION_SYSTEM_PROMPT = """You are a LIMS configuration assistant. You will be given the text content of
a laboratory Standard Operating Procedure (SOP) document and an example instrument
output file. Extract the following information and return it as a single JSON object.

Return ONLY valid JSON with this structure:
{
  "template_definition": {
    "experiment_name": "string",
    "description": "string or null",
    "protocol_steps": ["string", ...],
    "plate_layout": {
      "plate_type": "96 or 384",
      "wells": {
        "A1": {"condition": "sample", "role": "unknown"},
        ...
      }
    },
    "transfer_steps": [
      {
        "step": 1,
        "source_plate": "string or null",
        "source_well": "string or null",
        "dest_plate": "string or null",
        "dest_well": "string or null",
        "volume_ul": number or null,
        "mandatory_review": true
      }
    ],
    "result_columns": [
      {"name": "string", "data_type": "string|float|integer|boolean", "unit": "string or null"}
    ],
    "acceptance_criteria": "string or null",
    "mandatory_review_count": number
  },
  "parser_config": {
    "columns": [
      {"source_col": "string", "field_name": "string", "data_type": "string", "unit": "string or null"}
    ],
    "well_col": "string or null",
    "skip_rows": number
  },
  "worklist_config": {
    "steps": [
      {
        "step": 1,
        "source_plate": "string or null",
        "source_well_col": "string or null",
        "dest_plate": "string or null",
        "dest_well_col": "string or null",
        "volume_col": "string or null",
        "mandatory_review": true
      }
    ]
  }
}

Set mandatory_review=true for ALL fields that affect robot behavior (volumes,
positions, source/destination plates). The mandatory_review_count in template_definition
should be the total count of transfer_steps where mandatory_review=true.
If information is not present in the SOP, use null for optional fields and empty
arrays for lists. Do not invent information that is not in the SOP."""


class SOPParseService:
    """Creates SOP parse jobs and exposes the background task runner."""

    def __init__(self, db: Session, current_user=None) -> None:
        self.db = db
        self.current_user = current_user
        self.repo = SopParseJobRepository(db)

    def _user_id(self) -> Optional[uuid.UUID]:
        return self.current_user.id if self.current_user else None

    def create_job(
        self,
        sop_filename: Optional[str],
        instrument_filename: Optional[str],
        template_id: Optional[uuid.UUID] = None,
    ) -> SopParseJob:
        """Create a new pending job. Raises 409 if a pending job exists for the template."""
        if template_id:
            existing = self.repo.get_pending_for_template(template_id)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"A parse job is already pending or processing for this template "
                        f"(job id: {existing.id}). Wait for it to complete before submitting a new one."
                    ),
                )
        job = self.repo.create(
            sop_filename=sop_filename,
            instrument_filename=instrument_filename,
            created_by=self._user_id(),
        )
        self.db.flush()
        self.db.refresh(job)
        self.db.commit()
        return job

    def get_job(self, job_id: uuid.UUID) -> SopParseJob:
        job = self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parse job not found")
        return job

    def apply_job(self, job_id: uuid.UUID) -> dict:
        """
        Apply a completed SOP parse job by creating:
          - ExperimentTemplate (with template_definition from result)
          - InstrumentParser    (with parser_config from result)
          - RobotWorklistConfig (with worklist_config from result, if present)

        Links the job's experiment_template_id FK to the new template.
        Raises 404 if job not found, 409 if already applied, 422 if not complete.

        Returns a dict with {job_id, experiment_template_id, instrument_parser_id,
        robot_worklist_config_id}.
        """
        job = self.get_job(job_id)

        if job.status != SopParseJobStatus.complete:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Job status is '{job.status}' — only complete jobs can be applied.",
            )
        if job.experiment_template_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Job has already been applied "
                    f"(experiment_template_id={job.experiment_template_id})."
                ),
            )

        result = job.result or {}
        template_def = result.get("template_definition") or {}
        parser_cfg = result.get("parser_config") or {}
        worklist_cfg = result.get("worklist_config") or {}

        experiment_name = template_def.get("experiment_name") or (
            f"SOP Import — {job.sop_filename or job_id}"
        )
        description = template_def.get("description")
        user_id = self._user_id()

        # Create ExperimentTemplate
        template = ExperimentTemplate(
            name=experiment_name,
            description=description,
            template_definition=template_def,
            created_by=user_id,
            modified_by=user_id,
        )
        self.db.add(template)
        self.db.flush()  # get template.id

        # Create InstrumentParser
        parser_repo = InstrumentParserRepository(self.db)
        parser = parser_repo.create(
            template_id=template.id,
            name=f"{experiment_name} — parser",
            description=f"Auto-generated from SOP parse job {job_id}",
            parser_config=parser_cfg,
            created_by=user_id,
        )
        self.db.flush()

        # Create RobotWorklistConfig (only if worklist steps present)
        worklist_config_id: Optional[uuid.UUID] = None
        steps = worklist_cfg.get("steps") or []
        if steps:
            worklist_repo = RobotWorklistConfigRepository(self.db)
            worklist = worklist_repo.create(
                template_id=template.id,
                name=f"{experiment_name} — worklist",
                description=f"Auto-generated from SOP parse job {job_id}",
                worklist_config=worklist_cfg,
                created_by=user_id,
            )
            self.db.flush()
            worklist_config_id = worklist.id

        # Link job → template
        job.experiment_template_id = template.id
        self.db.flush()
        self.db.commit()
        self.db.refresh(template)
        self.db.refresh(parser)

        return {
            "job_id": job.id,
            "experiment_template_id": template.id,
            "instrument_parser_id": parser.id,
            "robot_worklist_config_id": worklist_config_id,
        }

    @staticmethod
    def run_extraction_background(
        job_id: uuid.UUID,
        sop_text: str,
        instrument_text: str,
    ) -> None:
        """
        Background task: call Claude API, parse result, update job status.
        Uses its own SessionLocal() — never shares a session with the HTTP layer.
        """
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            repo = SopParseJobRepository(db)
            job = repo.get_by_id(job_id)
            if not job:
                return

            repo.mark_processing(job)
            db.flush()

            if not ANTHROPIC_API_KEY:
                repo.mark_failed(job, "ANTHROPIC_API_KEY is not configured")
                db.commit()
                return

            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            user_message = (
                f"SOP content:\n\n{sop_text}\n\n"
                f"Example instrument output:\n\n{instrument_text}"
            )

            try:
                message = client.messages.create(
                    model="claude-opus-4-5-20251101",
                    max_tokens=4096,
                    system=_EXTRACTION_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_message}],
                )
                raw_text = message.content[0].text.strip()

                # Strip markdown code fences if Claude wrapped in ```json
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                    raw_text = raw_text.rsplit("```", 1)[0]

                result = json.loads(raw_text)
                repo.mark_complete(job, result)
                db.commit()

            except anthropic.APIError as e:
                repo.mark_failed(job, f"Anthropic API error: {str(e)}")
                db.commit()
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                repo.mark_failed(job, f"Claude returned malformed JSON: {str(e)}")
                db.commit()

        except Exception as e:
            try:
                repo = SopParseJobRepository(db)
                job = repo.get_by_id(job_id)
                if job:
                    repo.mark_failed(job, f"Unexpected error: {str(e)}")
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()
