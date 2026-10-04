"""Configuring-agent settings, named configurations, proposals, and atomic apply."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.configuring_agent_allow import STOP_BANNER, classify_call
from app.services.configuring_agent_apply import (
    AtomicSession,
    CannotExpress,
    PermissionDenied,
    error_text,
    execute_step,
)
from app.services.configuring_agent_chunk import split_with_headings
from app.services.configuring_agent_crypto import (
    MissingProviderKey,
    clear_stored_key,
    encrypt_secret,
    resolve_provider_key,
)
from app.services.configuring_agent_embeddings import EMBEDDING_MODEL, embed_texts
from app.services.configuring_agent_extract import UnsupportedFileType, detect_kind, extract_text
from app.services.configuring_agent_llm import ProviderError, list_models, propose
from app.services.configuring_agent_allow import PROVIDERS
from models.configuring_agent import (
    SETTINGS_ID,
    Configuration,
    ConfigurationChunk,
    ConfigurationDocument,
    ConfigurationItem,
    ConfigurationRun,
    ConfigurationStep,
    ConfiguringAgentSettings,
)
from models.user import User

MAX_FILE_BYTES = 10_485_760
SETTINGS_DENIED = "You can't change configuring-agent settings."


def _settings(db: Session) -> ConfiguringAgentSettings:
    row = db.query(ConfiguringAgentSettings).filter(ConfiguringAgentSettings.id == SETTINGS_ID).first()
    if row is None:
        row = ConfiguringAgentSettings(id=SETTINGS_ID, name="Configuring agent")
        db.add(row)
        db.flush()
    return row


def settings_payload(row: ConfiguringAgentSettings) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "agent_provider": row.agent_provider,
        "agent_model": row.agent_model,
        "key_set": bool(row.key_ciphertext),
    }


def save_provider_and_model(db: Session, user: User, provider: str, model: Optional[str]) -> ConfiguringAgentSettings:
    if provider not in PROVIDERS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provider must be one of openai, xai, or anthropic.")
    row = _settings(db)
    if row.agent_provider != provider:
        # The stored key belonged to the previous provider. Never reuse it.
        row.agent_provider = provider
        row.key_ciphertext = None
        row.agent_model = None
    if model is not None:
        row.agent_model = model.strip() or None
    row.modified_by = user.id
    db.commit()
    db.refresh(row)
    return row


def set_key(db: Session, user: User, api_key: str) -> ConfiguringAgentSettings:
    row = _settings(db)
    if not row.agent_provider:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick a provider before setting a key.")
    secret = (api_key or "").strip()
    if not secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Key is required.")
    row.key_ciphertext = encrypt_secret(secret)
    row.modified_by = user.id
    db.commit()
    db.refresh(row)
    return row


def clear_key(db: Session, user: User) -> ConfiguringAgentSettings:
    row = _settings(db)
    clear_stored_key(row)
    row.modified_by = user.id
    db.commit()
    db.refresh(row)
    return row


def provider_key(row: ConfiguringAgentSettings, provider: str) -> str:
    stored = row.key_ciphertext if row.agent_provider == provider else None
    try:
        return resolve_provider_key(provider, stored)
    except MissingProviderKey as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


def models_for(db: Session, provider: str) -> list[dict[str, str]]:
    row = _settings(db)
    key = provider_key(row, provider)
    try:
        return list_models(provider, key)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, exc.message) from exc


def _configuration(db: Session, user: User, configuration_id) -> Configuration:
    row = (
        db.query(Configuration)
        .filter(Configuration.id == configuration_id, Configuration.client_id == user.client_id)
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuration not found")
    return row


def create_configuration(db: Session, user: User, name: str, description: Optional[str]) -> Configuration:
    cleaned = (name or "").strip()
    if not cleaned:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A configuration needs a name.")
    exists = (
        db.query(Configuration)
        .filter(Configuration.client_id == user.client_id, Configuration.name == cleaned)
        .first()
    )
    if exists:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A configuration with that name already exists.")
    row = Configuration(
        id=uuid.uuid4(),
        client_id=user.client_id,
        name=cleaned,
        description=(description or "").strip() or None,
        created_by=user.id,
        modified_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_configurations(db: Session, user: User) -> list[Configuration]:
    return (
        db.query(Configuration)
        .filter(Configuration.client_id == user.client_id)
        .order_by(Configuration.name)
        .all()
    )


def configuration_payload(db: Session, row: Configuration) -> dict[str, Any]:
    documents = (
        db.query(ConfigurationDocument)
        .filter(ConfigurationDocument.configuration_id == row.id)
        .order_by(ConfigurationDocument.created_at)
        .all()
    )
    items = (
        db.query(ConfigurationItem)
        .filter(ConfigurationItem.configuration_id == row.id)
        .order_by(ConfigurationItem.created_at)
        .all()
    )
    runs = (
        db.query(ConfigurationRun)
        .filter(ConfigurationRun.configuration_id == row.id)
        .order_by(ConfigurationRun.created_at.desc())
        .all()
    )
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "created_by": row.created_by,
        "documents": [
            {
                "id": doc.id,
                "name": doc.name,
                "file_type": doc.file_type,
                "status": doc.status,
                "chunk_count": doc.chunk_count,
                "error_message": doc.error_message,
                "created_by": doc.created_by,
            }
            for doc in documents
        ],
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "kind": item.kind,
                "target_id": item.target_id,
                "detail": item.detail,
                "created_by": item.created_by,
            }
            for item in items
        ],
        "runs": [
            {
                "id": run.id,
                "name": run.name,
                "status": run.status,
                "banner": run.banner,
                "created_by": run.created_by,
            }
            for run in runs
        ],
    }


def add_document(db: Session, user: User, configuration_id, filename: str, data: bytes) -> ConfigurationDocument:
    configuration = _configuration(db, user, configuration_id)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is larger than 10 MB.")
    try:
        kind = detect_kind(data, filename)
        text = extract_text(data, kind)
    except UnsupportedFileType as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if not text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That file has no text to configure from.")
    labeled = split_with_headings(text)
    if not labeled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That file has no text to configure from.")
    doc = ConfigurationDocument(
        id=uuid.uuid4(),
        configuration_id=configuration.id,
        name=(filename or "upload").strip()[:255] or "upload",
        file_type=kind,
        status="processing",
        created_by=user.id,
    )
    db.add(doc)
    db.flush()
    try:
        to_embed = [f"[{heading}] {piece}" if heading else piece for piece, heading in labeled]
        vectors = embed_texts(to_embed)
        for index, ((piece, heading), vector) in enumerate(zip(labeled, vectors)):
            db.add(
                ConfigurationChunk(
                    id=uuid.uuid4(),
                    configuration_id=configuration.id,
                    document_id=doc.id,
                    content=piece,
                    embedding=vector,
                    embedding_model=EMBEDDING_MODEL,
                    chunk_index=index,
                    heading=heading or None,
                )
            )
        doc.content = text
        doc.status = "ready"
        doc.chunk_count = len(labeled)
        doc.embedding_model = EMBEDDING_MODEL
        configuration.modified_by = user.id
        db.commit()
        db.refresh(doc)
        return doc
    except Exception:
        db.rollback()
        raise


def _ready_documents(db: Session, configuration_id) -> int:
    return (
        db.query(ConfigurationDocument)
        .filter(
            ConfigurationDocument.configuration_id == configuration_id,
            ConfigurationDocument.status == "ready",
        )
        .count()
    )


def _excerpt(db: Session, configuration_id, text: str) -> list[str]:
    vector = embed_texts([text or "configuration"])[0]
    rows = (
        db.query(ConfigurationChunk)
        .filter(ConfigurationChunk.configuration_id == configuration_id)
        .order_by(ConfigurationChunk.embedding.cosine_distance(vector))
        .limit(8)
        .all()
    )
    excerpts = []
    for row in rows:
        if row.heading:
            excerpts.append(f"[{row.heading}] {row.content}")
        else:
            excerpts.append(row.content)
    return excerpts


def _key_for_run(db: Session) -> tuple[ConfiguringAgentSettings, str]:
    row = _settings(db)
    if not row.agent_provider or not row.agent_model:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Pick a provider and a model under Configuring agent settings before starting a run.",
        )
    return row, provider_key(row, row.agent_provider)


def _steps_from_proposal(parsed: dict) -> list[dict]:
    steps = parsed.get("steps")
    if isinstance(steps, list) and steps:
        return [step for step in steps if isinstance(step, dict)]
    if parsed.get("target") or parsed.get("gap"):
        return [parsed]
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "The model did not return any configuration steps.")


def _add_step(db: Session, run: ConfigurationRun, position: int, raw: dict) -> ConfigurationStep:
    call = raw.get("call") if isinstance(raw.get("call"), dict) else {}
    method = (call.get("method") or "") if call else ""
    path = (call.get("path") or "") if call else ""
    body = call.get("body") if call else None
    gap = (raw.get("gap") or "").strip() or None
    if method and path:
        classified = classify_call(method, path, body if isinstance(body, dict) else {})
        if not classified.ok:
            gap = classified.gap
            method, path, body = "", "", None
        group = classified.group
    else:
        group = raw.get("group") or "other"
        if not gap:
            gap = "This step does not name a configuration API."
    blocked = bool(gap)
    step = ConfigurationStep(
        id=uuid.uuid4(),
        run_id=run.id,
        position=position,
        group_name=group if group in {
            "schema_tables", "schema_columns", "layouts", "privileges", "relations", "other"
        } else "other",
        target=(str(raw.get("target") or "Configuration"))[:255],
        action=(str(raw.get("action") or "Change"))[:500],
        why=(str(raw.get("why") or ""))[:500] or "Requested by the lab file.",
        decision="pending",
        status="stopped" if blocked else "proposed",
        call_method=method or None,
        call_path=path or None,
        call_body=body if isinstance(body, (dict, list)) else None,
        gap=gap,
    )
    db.add(step)
    return step


def start_run(db: Session, user: User, configuration_id, goal_note: Optional[str]) -> ConfigurationRun:
    configuration = _configuration(db, user, configuration_id)
    if _ready_documents(db, configuration.id) < 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Add a lab file before starting a run. Empty input does not call the model.",
        )
    settings, key = _key_for_run(db)
    excerpts = _excerpt(db, configuration.id, goal_note or configuration.name)
    run = ConfigurationRun(
        id=uuid.uuid4(),
        configuration_id=configuration.id,
        name=f"{configuration.name} run",
        status="reading_inputs",
        goal_note=(goal_note or "").strip() or None,
        created_by=user.id,
        modified_by=user.id,
    )
    db.add(run)
    db.flush()
    try:
        parsed = propose(
            settings.agent_provider,
            settings.agent_model,
            key,
            chunks=excerpts,
            goal_note=run.goal_note,
        )
    except ProviderError as exc:
        run.status = "failed"
        run.error_message = exc.message
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, exc.message) from exc
    try:
        raw_steps = _steps_from_proposal(parsed)
    except HTTPException as exc:
        run.status = "failed"
        run.error_message = str(exc.detail)
        db.commit()
        raise
    stopped = False
    for index, raw in enumerate(raw_steps):
        step = _add_step(db, run, index, raw)
        if step.status == "stopped":
            stopped = True
            run.banner = STOP_BANNER
            run.stopped_count = 1
            break
    run.status = "stopped" if stopped else "proposing"
    db.commit()
    db.refresh(run)
    return run


def _run(db: Session, user: User, run_id) -> ConfigurationRun:
    row = (
        db.query(ConfigurationRun)
        .join(Configuration, Configuration.id == ConfigurationRun.configuration_id)
        .filter(ConfigurationRun.id == run_id, Configuration.client_id == user.client_id)
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return row


def step_payload(step: ConfigurationStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "position": step.position,
        "group": step.group_name,
        "target": step.target,
        "action": step.action,
        "why": step.why,
        "decision": step.decision,
        "status": step.status,
        "gap": step.gap,
        "error_message": step.error_message,
        "call": (
            {"method": step.call_method, "path": step.call_path, "body": step.call_body}
            if step.call_method and step.call_path
            else None
        ),
    }


def run_payload(run: ConfigurationRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "name": run.name,
        "configuration_id": run.configuration_id,
        "status": run.status,
        "goal_note": run.goal_note,
        "banner": run.banner,
        "error_message": run.error_message,
        "applied_count": run.applied_count,
        "skipped_count": run.skipped_count,
        "stopped_count": run.stopped_count,
        "created_by": run.created_by,
        "steps": [step_payload(step) for step in run.steps],
    }


def _step(run: ConfigurationRun, step_id) -> ConfigurationStep:
    for step in run.steps:
        if step.id == step_id:
            return step
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Step not found")


def accept_step(db: Session, user: User, run_id, step_id) -> ConfigurationRun:
    run = _run(db, user, run_id)
    step = _step(run, step_id)
    if step.gap or step.status == "stopped" or not step.call_path:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This step cannot be accepted. Skip it or send feedback.")
    step.decision = "accepted"
    step.status = "proposed"
    run.modified_by = user.id
    db.commit()
    db.refresh(run)
    return run


def skip_step(db: Session, user: User, run_id, step_id) -> ConfigurationRun:
    run = _run(db, user, run_id)
    step = _step(run, step_id)
    step.decision = "skipped"
    step.status = "skipped"
    run.modified_by = user.id
    db.commit()
    db.refresh(run)
    return run


def redo_step(db: Session, user: User, run_id, step_id, feedback: str) -> ConfigurationRun:
    note = (feedback or "").strip()
    if not note:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Feedback is required to redo a step.")
    run = _run(db, user, run_id)
    step = _step(run, step_id)
    settings, key = _key_for_run(db)
    excerpts = _excerpt(db, run.configuration_id, note)
    try:
        parsed = propose(
            settings.agent_provider,
            settings.agent_model,
            key,
            chunks=excerpts,
            goal_note=run.goal_note,
            feedback=note,
        )
    except ProviderError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, exc.message) from exc
    raw_steps = _steps_from_proposal(parsed)
    replacement = _add_step(db, run, step.position, raw_steps[0])
    # Carrier only. The original step is updated in place so redo does not insert a second row.
    step.group_name = replacement.group_name
    step.target = replacement.target
    step.action = replacement.action
    step.why = replacement.why
    step.decision = "pending"
    step.status = replacement.status
    step.call_method = replacement.call_method
    step.call_path = replacement.call_path
    step.call_body = replacement.call_body
    step.gap = replacement.gap
    step.error_message = None
    db.expunge(replacement)
    if step.status == "stopped":
        run.banner = STOP_BANNER
        run.status = "stopped"
        run.stopped_count = 1
    elif run.status == "stopped":
        run.status = "proposing"
        run.banner = None
    run.modified_by = user.id
    db.commit()
    db.refresh(run)
    return run


async def apply_run(db: Session, user: User, run_id) -> tuple[ConfigurationRun, int]:
    """Apply every accepted step or roll back. Returns the run and the HTTP status."""
    run = _run(db, user, run_id)
    accepted = [step for step in run.steps if step.decision == "accepted"]
    if not accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Accept at least one step before applying.")
    blocked = next((step for step in accepted if step.gap or step.status == "stopped" or not step.call_path), None)
    if blocked is not None:
        run.status = "stopped"
        run.banner = STOP_BANNER
        run.stopped_count = 1
        run.modified_by = user.id
        db.commit()
        db.refresh(run)
        return run, status.HTTP_200_OK

    _key_for_run(db)
    run_id_value = run.id
    failing_step_id = None
    atomic = AtomicSession(db)
    try:
        run.status = "applying"
        for step in accepted:
            failing_step_id = step.id
            changes = await execute_step(atomic, user, step.call_method, step.call_path, step.call_body or {})
            step.status = "applied"
            for change in changes:
                db.add(
                    ConfigurationItem(
                        id=uuid.uuid4(),
                        configuration_id=run.configuration_id,
                        run_id=run.id,
                        kind=change.kind,
                        name=(change.name or step.target)[:255],
                        target_id=change.target_id,
                        detail=step.action,
                        created_by=user.id,
                    )
                )
        skipped = sum(1 for step in run.steps if step.decision == "skipped")
        run.status = "done"
        run.banner = None
        run.error_message = None
        run.applied_count = len(accepted)
        run.skipped_count = skipped
        run.stopped_count = 0
        run.modified_by = user.id
        db.commit()
        db.refresh(run)
        return run, status.HTTP_200_OK
    except PermissionDenied as exc:
        db.rollback()
        return _record_failure(db, user, run_id_value, failing_step_id, exc.detail, permission=True)
    except CannotExpress as exc:
        db.rollback()
        return _record_failure(db, user, run_id_value, failing_step_id, exc.gap, stopped=True)
    except HTTPException as exc:
        db.rollback()
        return _record_failure(
            db,
            user,
            run_id_value,
            failing_step_id,
            error_text(exc),
            permission=exc.status_code == status.HTTP_403_FORBIDDEN,
        )
    except Exception:
        db.rollback()
        return _record_failure(
            db,
            user,
            run_id_value,
            failing_step_id,
            "Apply failed and every change from this apply was undone.",
        )


def _record_failure(db, user, run_id, step_id, message: str, permission: bool = False, stopped: bool = False):
    run = db.query(ConfigurationRun).filter(ConfigurationRun.id == run_id).first()
    if run is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Run disappeared during rollback")
    run.status = "stopped" if stopped else "failed"
    run.banner = STOP_BANNER if stopped else None
    run.error_message = None if stopped else message
    run.applied_count = 0
    run.stopped_count = 1 if stopped else 0
    run.modified_by = user.id
    for step in run.steps:
        if step.id == step_id:
            step.status = "stopped" if stopped else "failed"
            if stopped:
                step.gap = message
            else:
                step.error_message = message
    db.commit()
    db.refresh(run)
    code = status.HTTP_403_FORBIDDEN if permission else status.HTTP_200_OK
    return run, code
