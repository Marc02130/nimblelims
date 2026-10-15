"""Configuring-agent settings, named configurations, proposals, and atomic apply."""

from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy.exc import DBAPIError
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.configuring_agent_allow import STOP_BANNER, asks_for_a_change, classify_call, out_of_scope_request
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

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 10_485_760
SETTINGS_DENIED = "You can't change configuring-agent settings."


def _settings(db: Session) -> ConfiguringAgentSettings:
    row = db.query(ConfiguringAgentSettings).filter(ConfiguringAgentSettings.id == SETTINGS_ID).first()
    if row is None:
        row = ConfiguringAgentSettings(id=SETTINGS_ID, name="Configuring agent")
        db.add(row)
        db.flush()
    return row


def _settings_read(db: Session) -> ConfiguringAgentSettings:
    """Read-only settings lookup. Never adds or flushes a row (G8: no writes
    before or on a missing-key error)."""
    row = db.query(ConfiguringAgentSettings).filter(ConfiguringAgentSettings.id == SETTINGS_ID).first()
    return row if row is not None else ConfiguringAgentSettings(id=SETTINGS_ID, name="Configuring agent")


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
    row = _settings_read(db)
    key = provider_key(row, provider)
    release_db_for_model_call(db)
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
    row = _settings_read(db)
    if not row.agent_provider or not row.agent_model:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Pick a provider and a model under Configuring agent settings before starting a run.",
        )
    return row, provider_key(row, row.agent_provider)


_INSIDE_WORDS = re.compile(r"\b(field|column|attribute|entry|entries|value|values|option|row)s?\b", re.I)


def _adds_inside(present: str, raw: dict) -> bool:
    """The row adds something to an existing table ('add working solution volume
    field' on experiments): the table existing is not that field existing."""
    return present.startswith("table ") and bool(_INSIDE_WORDS.search(str(raw.get("action") or "")))


NO_STEPS_GAP = "The model proposed no configuration change for this request, so nothing can be applied."


def _steps_from_proposal(parsed: dict, target: Optional[str] = None) -> list[dict]:
    """The model's rows. Zero rows, or a bare refusal, is one stop row with the
    reason (D-6, UAT 1787efc: a redo returned 400 'no steps'), never an error."""
    steps = parsed.get("steps") if isinstance(parsed, dict) else None
    if isinstance(steps, list):
        rows = [step for step in steps if isinstance(step, dict)]
        if rows:
            return rows
    if isinstance(parsed, dict) and (parsed.get("target") or parsed.get("gap")):
        return [parsed]
    reason = ""
    if isinstance(parsed, dict):
        for key in ("gap", "reason", "refusal", "message", "banner", "note"):
            if isinstance(parsed.get(key), str) and parsed[key].strip():
                reason = parsed[key].strip()
                break
    return [{
        "group": "other",
        "target": target or "Configuration",
        "action": "No change proposed",
        "why": reason[:500] or "The model returned no steps.",
        "gap": f"{NO_STEPS_GAP} {reason}".strip()[:1000],
    }]


INCLUDED = "included"
EXCLUDED = "excluded"


def _depends_on(raw: dict, position: int) -> Optional[list[int]]:
    value = raw.get("depends_on")
    if not isinstance(value, list):
        return None
    positions = sorted({int(item) for item in value if isinstance(item, int) and 0 <= item < position})
    return positions or None


def _add_step(
    db: Session, run: ConfigurationRun, position: int, raw: dict, user: Optional[User] = None
) -> ConfigurationStep:
    """One proposal row. A row the APIs can't express is kept, stopped, with its reason (D-6)."""
    from app.services.configuring_agent_catalog import (
        column_home_gap,
        transition_gap,
        describe_change,
        existing_named,
        near_matches,
        resolve_body,
        resolve_path,
        reuse_gap,
    )

    call = raw.get("call") if isinstance(raw.get("call"), dict) else {}
    method = ((call.get("method") or "") if call else "").upper()
    path = (call.get("path") or "") if call else ""
    body = call.get("body") if call else None
    gap = (raw.get("gap") or "").strip() or None
    unchanged = False
    if method and path:
        classified = classify_call(method, path, body if isinstance(body, dict) else {})
        if not classified.ok:
            gap = classified.gap
        elif not gap:
            # UAT 145f6b3: a new table for a seed list, or per-run values as config.
            gap = reuse_gap(method, path, body)
        if classified.ok and not gap and user is not None:
            # Names -> ids and the model's key mistakes -> real field names. Stored
            # resolved so the row shows the real request; apply resolves again.
            path = resolve_path(db, user, method, path)
            body = resolve_body(db, user, method, path, body)
            again = classify_call(method, path, body if isinstance(body, dict) else {})
            if not again.ok:
                gap = again.gap
            elif describe_change(db, user, method, path, body)["changed"] is False:
                # G5: already there. A no-op, never a stop, even on a table
                # that can't take new fields.
                unchanged = True
            elif column_home_gap(db, user, method, path, body) or transition_gap(method, path, body):
                # D-5: say where the field belongs instead of a 422 at apply.
                gap = column_home_gap(db, user, method, path, body) or transition_gap(method, path, body)
            # Escalation is not frozen here: it is judged for the confirmer at view
            # and at apply (G1). Only API-expressibility stops are stored.
        group = classified.group
    else:
        group = raw.get("group") or "other"
        # D-6 (UAT 1787efc): stops win. A routing or asked-for request is a stop
        # even when its target names an existing table (routing_map). A call-less
        # row is No change only when the database holds the object and the row
        # asks for nothing but that object as it is (add/reuse), never a change.
        area = out_of_scope_request(raw)
        present = existing_named(db, user, raw.get("target")) if user is not None and not area else None
        if area:
            gap = area if not gap else f"{area} {gap}"
        elif present and not asks_for_a_change(raw) and not _adds_inside(present, raw):
            # G5 (UAT 06c630b): the model wrote a gap for something that already
            # exists. The database (not the gap text) confirms it: No change.
            unchanged, gap = True, None
        elif not gap:
            gap = "This step does not name a configuration API."
    near = []
    if method and path and not gap and not unchanged and user is not None:
        near = near_matches(db, user, method, path, body)
    blocked = bool(gap)
    if blocked:
        state = "stopped"
    elif unchanged:
        state = "unchanged"
    else:
        state = "proposed"
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
        # Every row starts included except a no-op rerun row. A stopped row stays
        # included until the user excludes it, so Apply refuses while it is in.
        # A near-match (item 4) also starts excluded: reuse the existing one, or
        # include the row if it really is different.
        decision=EXCLUDED if (unchanged or near) else INCLUDED,
        status=state,
        call_method=method or None,
        call_path=path or None,
        call_body=body if isinstance(body, (dict, list)) else None,
        gap=gap,
        depends_on=_depends_on(raw, position),
        stop_source=None,
    )
    db.add(step)
    return step


def _sync_stop_banner(run: ConfigurationRun) -> None:
    stopped = [step for step in run.steps if step.status == "stopped"]
    run.stopped_count = len(stopped)
    if stopped:
        run.banner = STOP_BANNER
    elif run.banner == STOP_BANNER:
        run.banner = None


def _catalog_for_prompt(db: Session, user: User) -> str:
    """Tables, lists, roles, container types with ids, for the model (UAT D-4/D-7)."""
    from app.services.configuring_agent_catalog import catalog_snapshot, catalog_text

    return catalog_text(catalog_snapshot(db, user))


@dataclass
class PendingRun:
    """What the model call needs, captured before the request returns."""

    run_id: Any
    user_id: Any
    client_id: Any
    provider: str
    model: str
    key: str
    excerpts: list
    goal_note: Optional[str]
    catalog: str


def begin_run(db: Session, user: User, configuration_id, goal_note: Optional[str]) -> tuple[ConfigurationRun, PendingRun]:
    """Validate and create the run (status reading_inputs). No model call yet.
    Commits only the run row: no catalog rows (D-3/L-4)."""
    configuration = _configuration(db, user, configuration_id)
    if _ready_documents(db, configuration.id) < 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Add a lab file before starting a run. Empty input does not call the model.",
        )
    settings, key = _key_for_run(db)
    excerpts = _excerpt(db, configuration.id, goal_note or configuration.name)
    catalog = _catalog_for_prompt(db, user)
    prior = _prior_text(_prior_calls(db, configuration.id))
    if prior:
        catalog = f"{catalog}\n\n{prior}" if catalog else prior
    run = ConfigurationRun(
        id=uuid.uuid4(),
        configuration_id=configuration.id,
        name=f"{configuration.name} run",
        status="reading_inputs",
        goal_note=(goal_note or "").strip() or None,
        agent_provider=settings.agent_provider,
        agent_model=settings.agent_model,
        created_by=user.id,
        modified_by=user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    pending = PendingRun(
        run_id=run.id,
        user_id=user.id,
        client_id=user.client_id,
        provider=settings.agent_provider,
        model=settings.agent_model,
        key=key,
        excerpts=list(excerpts),
        goal_note=run.goal_note,
        catalog=catalog,
    )
    return run, pending


DB_LOST_MESSAGE = (
    "Lost the database connection while saving the model's proposal ({kind}). "
    "Nothing from this run was saved. Start a new run."
)


def release_db_for_model_call(db: Session) -> None:
    """End the open transaction before a slow model call (120-300 s).

    UAT 67481e9: the propose step held a transaction open through the model
    call, so idle_in_transaction_session_timeout (60 s, #162) killed the
    connection and every run failed with OperationalError. Commit ends the
    transaction and hands the connection back to the pool; the session opens a
    fresh transaction (RLS GUCs re-applied by the after_begin hook) on next use.
    Callers must not touch the session between this and the model reply.
    """
    db.commit()


def finish_run(db: Session, user: User, pending: PendingRun, raise_errors: bool = True) -> ConfigurationRun:
    """Call the model and store the proposal rows. Used inline (start_run) and
    from the background task (item 5: grok-4.7 takes 96-300 s)."""
    release_db_for_model_call(db)
    try:
        parsed = propose(
            pending.provider,
            pending.model,
            pending.key,
            chunks=pending.excerpts,
            goal_note=pending.goal_note,
            # The confirmer isn't known yet; send no one's permissions (G1).
            permissions=None,
            catalog=pending.catalog,
        )
        raw_steps = _steps_from_proposal(parsed)
    except ProviderError as exc:
        run = db.query(ConfigurationRun).filter(ConfigurationRun.id == pending.run_id).one()
        run.status = "failed"
        run.error_message = exc.message or "The model call failed with no detail. Start a new run."
        db.commit()
        if raise_errors:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, exc.message) from exc
        return run
    except HTTPException as exc:
        run = db.query(ConfigurationRun).filter(ConfigurationRun.id == pending.run_id).one()
        run.status = "failed"
        run.error_message = str(exc.detail or "") or f"The run failed (HTTP {exc.status_code}). Start a new run."
        db.commit()
        if raise_errors:
            raise
        return run
    run = db.query(ConfigurationRun).filter(ConfigurationRun.id == pending.run_id).one()
    # Keep every row. Each stop stays in place with its reason (D-6); no first-stop break.
    stopped = 0
    seen = set()
    index = -1
    for index, raw in enumerate(raw_steps):
        step = _add_step(db, run, index, raw, user)
        seen.add(_call_key(step.call_method, step.call_path, step.call_body))
        if step.status == "stopped":
            stopped += 1
    # Rerun coverage (UAT 7d84e07): the model dropped Request ID and Sample Log
    # Number on the CMDL rerun. Calls an earlier run of this source proposed or
    # applied, and this reply left out, are kept: No change when the database
    # has them (G5), proposed otherwise.
    for prior in _prior_calls(db, run.configuration_id, exclude_run=run.id):
        key = _call_key(prior.call_method, prior.call_path, prior.call_body)
        if key in seen:
            continue
        index += 1
        step = _add_step(db, run, index, {
            "group": prior.group_name,
            "target": prior.target,
            "action": prior.action,
            "why": f"Kept from an earlier run of this source. {prior.why or ''}".strip(),
            "call": {"method": prior.call_method, "path": prior.call_path, "body": prior.call_body},
        }, user)
        resolved = _call_key(step.call_method, step.call_path, step.call_body)
        if resolved in seen:
            # Same call once names resolve to ids: the model kept it after all.
            db.expunge(step)
            index -= 1
            continue
        seen.add(resolved)
        if step.status == "stopped":
            stopped += 1
    run.stopped_count = stopped
    run.banner = STOP_BANNER if stopped else None
    run.status = "stopped" if stopped else "proposing"
    db.commit()
    db.refresh(run)
    return run


CARRIED_STATUSES = ("applied", "proposed", "unchanged")


def _call_key(method, path, body) -> tuple:
    data = body if isinstance(body, dict) else {}
    name = str(data.get("display_name") or data.get("name") or data.get("physical_name") or "").strip().lower()
    return (
        (method or "").upper(), (path or "").rstrip("/"), name,
        str(data.get("table_id") or data.get("table") or "").lower(),
        str(data.get("source_sample_type") or "").lower(), str(data.get("allowed_dest_sample_type") or "").lower(),
    )


def _prior_calls(db: Session, configuration_id, exclude_run=None) -> list:
    """Calls earlier runs of this configuration proposed or applied, newest first,
    one per call key. Stops and refused rows are not carried."""
    query = (
        db.query(ConfigurationStep)
        .join(ConfigurationRun, ConfigurationRun.id == ConfigurationStep.run_id)
        .filter(
            ConfigurationRun.configuration_id == configuration_id,
            ConfigurationStep.status.in_(CARRIED_STATUSES),
            ConfigurationStep.call_method.isnot(None),
            ConfigurationStep.call_path.isnot(None),
        )
    )
    if exclude_run is not None:
        query = query.filter(ConfigurationRun.id != exclude_run)
    rows = query.order_by(ConfigurationRun.created_at.desc(), ConfigurationStep.position).all()
    out, keys = [], set()
    for row in rows:
        key = _call_key(row.call_method, row.call_path, row.call_body)
        if key not in keys:
            keys.add(key)
            out.append(row)
    return out


def _prior_text(rows: list) -> str:
    if not rows:
        return ""
    lines = [
        "Earlier runs of this source proposed or applied these. Keep every one that the excerpts still "
        "support: send its normal call again (the server shows existing ones as No change)."
    ]
    for row in rows[:60]:
        lines.append(f"- {row.call_method} {row.call_path} {row.target}")
    return "\n".join(lines)


def start_run(db: Session, user: User, configuration_id, goal_note: Optional[str]) -> ConfigurationRun:
    """Synchronous run: begin, call the model, store the rows."""
    _run_row, pending = begin_run(db, user, configuration_id, goal_note)
    return finish_run(db, user, pending)


# Tests point the background task at their own session; production uses SessionLocal.
BACKGROUND_SESSION_FACTORY = None


def run_in_background(pending: PendingRun, session_factory=None) -> None:
    """Background task body: its own session, the starter's RLS context."""
    from app.database import SessionLocal, set_rls_context

    factory = session_factory or BACKGROUND_SESSION_FACTORY
    owned = factory is None
    db = SessionLocal() if owned else factory()
    try:
        if owned:
            set_rls_context(db, user_id=str(pending.user_id), client_id=str(pending.client_id))
        user = db.query(User).filter(User.id == pending.user_id).one()
        try:
            finish_run(db, user, pending, raise_errors=False)
        except Exception as exc:  # noqa: BLE001 - a run must never stay reading_inputs
            logger.exception("configuring agent background run failed")
            if isinstance(exc, DBAPIError):
                message = DB_LOST_MESSAGE.format(kind=type(exc).__name__)
            else:
                message = f"The run failed while reading the model's proposal ({type(exc).__name__}). Start a new run."
            try:
                db.rollback()
                run = db.query(ConfigurationRun).filter(ConfigurationRun.id == pending.run_id).first()
                if run is not None and (run.status == "reading_inputs" or (run.status == "failed" and not run.error_message)):
                    run.status = "failed"
                    run.error_message = message
                    db.commit()
            except DBAPIError:
                # Still no database: expire_stale marks the run failed on the next poll.
                logger.exception("could not record the failed configuring agent run")
    finally:
        if owned:
            db.close()


STALE_MESSAGE = "The model call did not finish. Start a new run."


def expire_stale(db: Session, run: ConfigurationRun) -> ConfigurationRun:
    """A run still reading inputs well past the model timeout (e.g. the server
    restarted mid-call) is marked failed, so polling ends."""
    from app.services.configuring_agent_llm import model_timeout

    if run.status != "reading_inputs" or run.created_at is None:
        return run
    created = run.created_at
    now = datetime.now(timezone.utc) if created.tzinfo else datetime.utcnow()
    if (now - created).total_seconds() > model_timeout() + 120:
        run.status = "failed"
        run.error_message = STALE_MESSAGE
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


def _step_facts(step: ConfigurationStep, db: Optional[Session] = None, viewer: Optional[User] = None) -> dict[str, Any]:
    from app.services.configuring_agent_allow import needs_second_confirm, verb_for
    from app.services.configuring_agent_apply import escalation_gap, missing_permission

    if not (step.call_method and step.call_path):
        return {"verb": None, "second_confirm": False, "needs_permission": None, "escalation": None}
    classified = classify_call(step.call_method, step.call_path, step.call_body if isinstance(step.call_body, dict) else {})
    needs = None
    escalation = None
    if viewer is not None and db is not None and classified.ok:
        needs = missing_permission(viewer, db, classified)
        # G1: escalation is re-checked for the viewer (the confirmer), not only the starter.
        escalation = escalation_gap(db, viewer, step.call_method, step.call_path, step.call_body)
    return {
        "escalation": escalation,
        "verb": verb_for(step.call_method, step.call_path, step.call_body),
        "second_confirm": bool(classified.ok and needs_second_confirm(
            step.call_method, step.call_path, step.call_body, classified.kind
        )),
        "needs_permission": needs,
    }


def _diff(step: ConfigurationStep, db: Optional[Session], viewer: Optional[User]) -> Optional[dict[str, Any]]:
    """Before/after against the live configuration (G5). None once applied."""
    from app.services.configuring_agent_catalog import describe_change

    if db is None or viewer is None or not (step.call_method and step.call_path) or step.status == "applied":
        return None
    try:
        return describe_change(db, viewer, step.call_method, step.call_path, step.call_body)
    except Exception:  # noqa: BLE001 - advisory only
        return None


def _near(step: ConfigurationStep, db: Optional[Session], viewer: Optional[User]) -> list[str]:
    """Existing objects this new row nearly duplicates (item 4)."""
    from app.services.configuring_agent_catalog import near_matches

    if db is None or viewer is None or step.status not in ("proposed",) or not step.call_path:
        return []
    try:
        return near_matches(db, viewer, step.call_method, step.call_path, step.call_body)
    except Exception:  # noqa: BLE001 - advisory only
        return []


def step_payload(step: ConfigurationStep, db: Optional[Session] = None, viewer: Optional[User] = None) -> dict[str, Any]:
    facts = _step_facts(step, db, viewer)
    return {
        "diff": _diff(step, db, viewer),
        "near_matches": _near(step, db, viewer),
        "id": step.id,
        "position": step.position,
        "group": step.group_name,
        "target": step.target,
        "action": step.action,
        "why": step.why,
        "decision": step.decision,
        "included": step.decision in (INCLUDED, "accepted"),
        # A row that is an escalation for this viewer is shown as a stop in place.
        "status": "stopped" if facts["escalation"] and step.status != "applied" else step.status,
        "gap": step.gap or facts["escalation"],
        "stopped_for_viewer": bool(facts["escalation"] and not step.gap),
        "retryable": _retryable(step),
        "error_message": step.error_message,
        "depends_on": step.depends_on or [],
        "verb": facts["verb"],
        "second_confirm": facts["second_confirm"],
        # Re-evaluated for whoever is looking (the confirmer), not the starter.
        "needs_permission": facts["needs_permission"],
        "call": (
            {"method": step.call_method, "path": step.call_path, "body": step.call_body}
            if step.call_method and step.call_path
            else None
        ),
    }


def run_payload(run: ConfigurationRun, db: Optional[Session] = None, viewer: Optional[User] = None) -> dict[str, Any]:
    steps = [step_payload(step, db, viewer) for step in run.steps]
    # Stops as this viewer sees them, including escalations that are stops only
    # for this viewer (UAT: the banner and count missed them).
    stopped = sum(1 for row in steps if row["status"] == "stopped")
    banner = run.banner
    if stopped and run.status != "done" and not banner:
        banner = STOP_BANNER
    elif not stopped and banner == STOP_BANNER:
        banner = None
    return {
        "id": run.id,
        "name": run.name,
        "configuration_id": run.configuration_id,
        "status": run.status,
        "goal_note": run.goal_note,
        "banner": banner,
        "error_message": run.error_message,
        "applied_count": run.applied_count,
        "skipped_count": run.skipped_count,
        "stopped_count": stopped,
        "created_by": run.created_by,
        "confirmed_by": run.confirmed_by,
        "confirmed_at": run.confirmed_at.isoformat() if run.confirmed_at else None,
        "agent_provider": run.agent_provider,
        "agent_model": run.agent_model,
        "steps": steps,
    }


def _step(run: ConfigurationRun, step_id) -> ConfigurationStep:
    for step in run.steps:
        if step.id == step_id:
            return step
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Step not found")


def _is_included(step: ConfigurationStep) -> bool:
    return step.decision in (INCLUDED, "accepted")


def set_included(db: Session, user: User, run_id, step_id, include: bool) -> ConfigurationRun:
    """The per-row include control (L-1). Nothing is written to configuration."""
    run = _run(db, user, run_id)
    if run.status in ("done", "applying"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This run was already applied.")
    step = _step(run, step_id)
    if not include:
        dependents = [
            other.position + 1
            for other in run.steps
            if _is_included(other) and other.id != step.id and step.position in (other.depends_on or [])
        ]
        if dependents:
            raise ApplyRefused(
                status.HTTP_409_CONFLICT,
                f"Row {', '.join(map(str, dependents))} depends on row {step.position + 1}. "
                f"Exclude row {', '.join(map(str, dependents))} first.",
                dependents + [step.position + 1],
                reason="dependency",
            )
    step.decision = INCLUDED if include else EXCLUDED
    run.modified_by = user.id
    db.commit()
    db.refresh(run)
    return run


def accept_step(db: Session, user: User, run_id, step_id) -> ConfigurationRun:
    """Legacy name for include."""
    return set_included(db, user, run_id, step_id, True)


def skip_step(db: Session, user: User, run_id, step_id) -> ConfigurationRun:
    """Legacy name for exclude."""
    return set_included(db, user, run_id, step_id, False)


def redo_step(db: Session, user: User, run_id, step_id, feedback: str) -> ConfigurationRun:
    note = (feedback or "").strip()
    if not note:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Feedback is required to redo a step.")
    run = _run(db, user, run_id)
    step = _step(run, step_id)
    settings, key = _key_for_run(db)
    provider, model = settings.agent_provider, settings.agent_model
    excerpts = _excerpt(db, run.configuration_id, note)
    catalog = _catalog_for_prompt(db, user)
    goal_note = run.goal_note
    release_db_for_model_call(db)
    try:
        parsed = propose(
            provider,
            model,
            key,
            chunks=excerpts,
            goal_note=goal_note,
            feedback=note,
            # The confirmer isn't known yet; send no one's permissions (G1).
            permissions=None,
            catalog=catalog,
        )
    except ProviderError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, exc.message) from exc
    try:
        run = _run(db, user, run_id)
        step = _step(run, step_id)
    except DBAPIError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Lost the database connection after the model replied. Nothing changed; redo the step again.",
        ) from exc
    raw_steps = _steps_from_proposal(parsed, step.target)
    replacement = _add_step(db, run, step.position, raw_steps[0], user)
    # Carrier only. The original step is updated in place so redo does not insert a second row.
    step.group_name = replacement.group_name
    step.target = replacement.target
    step.action = replacement.action
    step.why = replacement.why
    step.decision = replacement.decision
    step.status = replacement.status
    step.call_method = replacement.call_method
    step.call_path = replacement.call_path
    step.call_body = replacement.call_body
    step.gap = replacement.gap
    step.depends_on = replacement.depends_on
    step.stop_source = None
    step.error_message = None
    db.expunge(replacement)
    _sync_stop_banner(run)
    if run.stopped_count:
        run.status = "stopped"
    elif run.status == "stopped":
        run.status = "proposing"
    run.modified_by = user.id
    db.commit()
    db.refresh(run)
    return run


class ApplyRefused(HTTPException):
    """Apply refused before any write. Carries the reason and the rows involved."""

    def __init__(self, code: int, message: str, rows: Optional[list[int]] = None, reason: str = "refused"):
        super().__init__(code, {"message": message, "reason": reason, "rows": rows or []})


def _gate(db: Session, user: User, run: ConfigurationRun, included: list[ConfigurationStep], second_confirm: bool) -> None:
    """Every check that must pass before the first write. Raises ApplyRefused."""
    from app.services.configuring_agent_allow import needs_second_confirm
    from app.services.configuring_agent_apply import escalation_gap, missing_permission

    if not included:
        raise ApplyRefused(status.HTTP_400_BAD_REQUEST, "Include at least one change.", reason="empty")
    # 1. Any included stop refuses Apply (D-6).
    stopped = [
        step for step in included
        if (step.status == "stopped" or step.gap or not step.call_path) and not _retryable(step)
    ]
    if stopped:
        rows = [step.position + 1 for step in stopped]
        raise ApplyRefused(
            status.HTTP_409_CONFLICT,
            f"Apply writes nothing while an included row is stopped (row {', '.join(map(str, rows))}). "
            "Exclude it or fix it.",
            rows,
            reason="stopped",
        )
    # 2. An included row may not depend on an excluded stopped row.
    by_position = {step.position: step for step in run.steps}
    for step in included:
        for dep in step.depends_on or []:
            parent = by_position.get(dep)
            if parent is None or _is_included(parent) or parent.status == "unchanged":
                continue
            if parent.status == "stopped":
                message = (
                    f"Row {step.position + 1} depends on row {dep + 1}, which is stopped. "
                    f"Exclude row {step.position + 1} too, or fix row {dep + 1}."
                )
            else:
                message = (
                    f"Row {step.position + 1} depends on row {dep + 1}, which is excluded. "
                    f"Include row {dep + 1}, or exclude row {step.position + 1} too."
                )
            raise ApplyRefused(
                status.HTTP_409_CONFLICT, message, [step.position + 1, dep + 1], reason="dependency"
            )
    # 3. Scope is the confirming user's own permissions (L-2), checked before any write.
    for step in included:
        classified = classify_call(step.call_method, step.call_path, step.call_body if isinstance(step.call_body, dict) else {})
        needs = missing_permission(user, db, classified)
        if needs:
            raise ApplyRefused(
                status.HTTP_403_FORBIDDEN,
                f"Row {step.position + 1} needs {needs}. You can't apply it.",
                [step.position + 1],
                reason="permission",
            )
        gap = escalation_gap(db, user, step.call_method, step.call_path, step.call_body)
        if gap:
            raise ApplyRefused(
                status.HTTP_409_CONFLICT, f"Row {step.position + 1}: {gap}", [step.position + 1], reason="escalation"
            )
    # 4. Second confirm for roles/privileges, schema, set-inactive, amount -> 0 (L-1).
    high = [
        step.position + 1
        for step in included
        if needs_second_confirm(
            step.call_method,
            step.call_path,
            step.call_body,
            classify_call(step.call_method, step.call_path, step.call_body if isinstance(step.call_body, dict) else {}).kind,
        )
    ]
    if high and not second_confirm:
        raise ApplyRefused(
            status.HTTP_409_CONFLICT,
            "These changes need a second confirm: you are responsible for these changes.",
            high,
            reason="second_confirm",
        )


def apply_run(
    db: Session, user: User, run_id, second_confirm: bool = False
) -> tuple[ConfigurationRun, int]:
    """Apply exactly the included rows in one transaction, or roll back. Returns run and HTTP status."""
    run = _run(db, user, run_id)
    if run.status == "done":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This run was already applied. Start a new run to change more.")
    included = [step for step in run.steps if _is_included(step)]
    _gate(db, user, run, included, second_confirm)

    settings, _key = _key_for_run(db)
    provider = run.agent_provider or settings.agent_provider
    model = run.agent_model or settings.agent_model
    run_id_value = run.id
    failing_step_id = None
    atomic = AtomicSession(db)
    try:
        run.status = "applying"
        applied = 0
        for step in sorted(included, key=lambda item: item.position):
            failing_step_id = step.id
            if _retryable(step):
                step.status, step.gap, step.stop_source = "proposed", None, None
            changes = execute_step(atomic, user, step.call_method, step.call_path, step.call_body or {})
            if changes and all(change.noop for change in changes):
                # Rerun no-op (G5): already in place. Nothing written, no ledger row.
                step.status = "unchanged"
                continue
            step.status = "applied"
            applied += 1
            for change in changes:
                if change.noop:
                    continue
                db.add(
                    ConfigurationItem(
                        id=uuid.uuid4(),
                        configuration_id=run.configuration_id,
                        run_id=run.id,
                        kind=change.kind,
                        name=(change.name or step.target)[:255],
                        target_id=change.target_id,
                        detail=step.action,
                        agent_assisted=True,
                        agent_provider=provider,
                        agent_model=model,
                        created_by=user.id,
                    )
                )
        run.status = "done"
        run.banner = None
        run.error_message = None
        run.applied_count = applied
        run.skipped_count = sum(1 for step in run.steps if not _is_included(step))
        run.stopped_count = 0
        run.confirmed_by = user.id
        run.confirmed_at = datetime.now(timezone.utc)
        run.agent_provider = provider
        run.agent_model = model
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
        if exc.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY):
            # G2 (Marc 2026-10-11): the API can't express this row. Show it as a stop
            # in place with the API's reason. The whole apply has already rolled back.
            return _record_failure(
                db, user, run_id_value, failing_step_id, api_stop_reason(exc), stopped=True, api=True
            )
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


API_STOP_PREFIX = "The API refused this change"


def api_stop_reason(exc: HTTPException) -> str:
    return f"{API_STOP_PREFIX} ({exc.status_code}): {error_text(exc)}"


def _retryable(step: ConfigurationStep) -> bool:
    """A stop the API raised at apply time (422/404). The cause may be fixed outside
    the run (e.g. the missing record created), so the next Apply retries it."""
    # Only the explicit flag counts. Gap text is never trusted: the model writes gaps.
    return step.status == "stopped" and step.stop_source == "api" and bool(step.call_path)


def _record_failure(
    db, user, run_id, step_id, message: str, permission: bool = False, stopped: bool = False, api: bool = False
):
    run = db.query(ConfigurationRun).filter(ConfigurationRun.id == run_id).first()
    if run is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Run disappeared during rollback")
    run.status = "stopped" if stopped else "failed"
    run.banner = STOP_BANNER if stopped else None
    run.error_message = None if stopped else (message or "Apply failed with no detail; nothing was changed.")
    run.applied_count = 0
    run.modified_by = user.id
    for step in run.steps:
        if step.status == "applied":
            # Rolled back with the rest of the transaction.
            step.status = "proposed"
        if step.id == step_id:
            step.status = "stopped" if stopped else "failed"
            # The only place a stop is marked as raised by the API (retryable).
            step.stop_source = "api" if (stopped and api) else None
            if stopped:
                step.gap = message
            else:
                step.error_message = message
    # G6: recount every stop on the run, not 1/0.
    run.stopped_count = sum(1 for step in run.steps if step.status == "stopped")
    db.commit()
    db.refresh(run)
    code = status.HTTP_403_FORBIDDEN if permission else status.HTTP_200_OK
    return run, code
