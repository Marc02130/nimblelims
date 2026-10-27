"""One provider per run. Models come from that provider's live list. No fixed catalog."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import logging

import httpx

from app.services.configuring_agent_allow import PROVIDERS, not_schema_tables

OPENAI_MODELS = "https://api.openai.com/v1/models"
XAI_MODELS = "https://api.x.ai/v1/models"
ANTHROPIC_MODELS = "https://api.anthropic.com/v1/models"
ANTHROPIC_VERSION = "2023-06-01"


DEFAULT_TIMEOUT_S = 300.0


def model_timeout() -> float:
    """Seconds to wait for the model. CONFIGURING_AGENT_TIMEOUT_S, default 300.

    90 s was too short for large reasoning models in UAT (grok-4.7).
    """
    raw = os.getenv("CONFIGURING_AGENT_TIMEOUT_S", "").strip()
    try:
        value = float(raw) if raw else DEFAULT_TIMEOUT_S
    except ValueError:
        return DEFAULT_TIMEOUT_S
    return value if value > 0 else DEFAULT_TIMEOUT_S


_ACCOUNT_ID = re.compile(
    r"\b(team|organi[sz]ation|org|account|project|workspace|tenant)(s?)\b(\s*(?:id)?\s*[:=#]?\s*[\"']?)"
    r"((?=[A-Za-z_-]*\d)[A-Za-z0-9][A-Za-z0-9_-]{5,})",  # ids carry a digit; plain words don't
    re.I,
)
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_PREFIXED_ID = re.compile(r"\b(org|proj|acct|team|user)-[A-Za-z0-9]{8,}\b")


def redact_ids(text: str) -> str:
    """Hide team/org/account ids that providers echo in errors (UAT 67481e9:
    an xAI 404 showed the team id)."""
    if not text:
        return text
    text = _ACCOUNT_ID.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}[redacted]", text)
    text = _PREFIXED_ID.sub("[redacted]", text)
    return _UUID.sub("[redacted]", text)


class ProviderError(Exception):
    def __init__(self, message: str):
        message = redact_ids(message)
        self.message = message
        super().__init__(message)


class BadReply(ProviderError):
    """The model answered, but not with usable JSON (prose, fences, truncation,
    empty content). Retried once with a JSON-only reminder."""


log = logging.getLogger(__name__)
PARSE_ATTEMPTS = 2
RETRY_NOTE = (
    "Your previous reply could not be parsed as JSON{why}. Reply again with the complete JSON object only: "
    "no markdown, no text before or after it. Keep each why short so the reply is not cut off."
)


def list_models(provider: str, api_key: str) -> list[dict[str, str]]:
    if provider not in PROVIDERS:
        raise ProviderError(f"Provider must be one of: {', '.join(PROVIDERS)}.")
    if provider == "openai":
        payload = _get_json(OPENAI_MODELS, {"Authorization": f"Bearer {api_key}"})
        return [{"id": row["id"], "display_name": row["id"]} for row in payload.get("data") or [] if row.get("id")]
    if provider == "xai":
        payload = _get_json(XAI_MODELS, {"Authorization": f"Bearer {api_key}"})
        return [{"id": row["id"], "display_name": row["id"]} for row in payload.get("data") or [] if row.get("id")]
    rows: list[dict[str, str]] = []
    after_id = None
    for _ in range(5):
        params = {"limit": 100}
        if after_id:
            params["after_id"] = after_id
        payload = _get_json(
            ANTHROPIC_MODELS,
            {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION},
            params=params,
        )
        for row in payload.get("data") or []:
            model_id = row.get("id")
            if not model_id:
                continue
            rows.append({"id": model_id, "display_name": row.get("display_name") or model_id})
        if not payload.get("has_more"):
            break
        after_id = payload.get("last_id")
        if not after_id:
            break
    return rows


def propose(provider: str, model: str, api_key: str, *, chunks: list[str], goal_note: str | None, feedback: str | None = None, permissions: list[str] | None = None, catalog: str | None = None) -> dict[str, Any]:
    """Ask the stored provider and model for configuration steps. Returns parsed JSON."""
    if provider not in PROVIDERS:
        raise ProviderError(f"Provider must be one of: {', '.join(PROVIDERS)}.")
    if not model:
        raise ProviderError("No model is selected.")
    system = _system_prompt(permissions, catalog)
    user = _user_prompt(chunks, goal_note, feedback)
    last: BadReply | None = None
    for attempt in range(PARSE_ATTEMPTS):
        prompt = user if last is None else user + "\n\n" + RETRY_NOTE.format(why=_why(last))
        try:
            return _parse_json(_call(provider, model, api_key, system, prompt))
        except BadReply as exc:
            last = exc
            log.warning("configuring agent: unusable model reply (attempt %s): %s", attempt + 1, exc.message)
    raise ProviderError("The model did not return configuration JSON, twice. Start the run again.")


def _why(exc: "BadReply") -> str:
    return " (it was cut off)" if "cut off" in exc.message else ""


def complete(provider: str, model: str, api_key: str, system: str, user: str) -> str:
    """One system+user call to the chosen provider; returns the reply text.

    Shared by the configuring agent and SOP parse. Errors are ProviderError
    (ids redacted) or BadReply."""
    if provider not in PROVIDERS:
        raise ProviderError(f"Provider must be one of: {', '.join(PROVIDERS)}.")
    if not model:
        raise ProviderError("No model is selected.")
    return _call(provider, model, api_key, system, user)


def _call(provider: str, model: str, api_key: str, system: str, user: str) -> str:
    if provider == "anthropic":
        return _anthropic(model, api_key, system, user)
    url = "https://api.openai.com/v1/chat/completions" if provider == "openai" else "https://api.x.ai/v1/chat/completions"
    return _openai_compatible(url, model, api_key, system, user)


def _system_prompt(permissions: list[str] | None = None, catalog: str | None = None) -> str:
    """Scope is the confirming user's permissions, not the Schema catalog (L-2).

    The routes and body formats come from the real routers' schemas, and the
    catalog block carries real ids (UAT 145f6b3: D-4, D-5, D-7)."""
    from app.services.configuring_agent_catalog import route_formats_text

    hidden = ", ".join(not_schema_tables())
    held = ", ".join(sorted(permissions or [])) or "none listed"
    return (
        "You propose NimbleLIMS configuration. Reply with JSON only, no markdown. "
        "Shape: {\"steps\":[{\"group\":\"schema_tables|schema_columns|layouts|privileges|relations|other\","
        "\"target\":\"...\",\"action\":\"...\",\"why\":\"one line\",\"depends_on\":[0],"
        "\"call\":{\"method\":\"POST\",\"path\":\"/v1/schema/columns\",\"body\":{}}}]} "
        "depends_on lists the zero-based positions of earlier steps this step needs; omit it when none. "
        "If no existing API can express a step, that step has \"gap\" (plain words) and no call. "
        "Do not invent a workaround. List every step, including the ones with a gap. "
        "Follow the lab process in the file excerpts. Do not assume every lab uses the same method. "
        "Do not invent needs the excerpts do not state. "
        "You act with the confirming user's own permissions and nothing more. "
        + (f"That user holds: {held}. " if permissions else
           "Permissions are checked for the person who confirms, at confirm time; do not assume any. ")
        + "Any table the user can change through an existing API is in scope. "
        "The APIs still refuse new columns on system tables and on asked_for, tests, results, containers, "
        "contents, routing_map, and work_orders; such a change is a gap. "
        f"Not schema tables: {hidden}. Do not add columns on them. "
        "List values use POST /lists and POST /lists/{name}/entries, group other. "
        "A sample-type transition's operation is derivative or pool. A derivative changes the sample type "
        "and creates a child sample (DNA extraction from blood, Blood to Plasma); an aliquot keeps the "
        "sample type in a new container and needs no transition. "
        "Never drop and never delete. To retire a list, entry, role, or transition, PATCH active false. "
        "To retire a table or column, POST its /deprecate route. To retire a container, "
        "PATCH /containers/{container_id}/contents/{sample_id} with {\"amount\": 0}. "
        "Relations are one_to_many or one_to_one on an existing foreign key. Never many_to_many. "
        "Do not call asked-for, routing, ELN process definitions, parsers, results, custom fields, "
        "workflow templates, or receive. Never grant privileges: do not grant schema:edit, do not give "
        "any role a permission the user does not hold, and do not change the user's own role. "
        "Do not create users. "
        "Experiment templates may be created with POST /v1/experiment-templates when the excerpts ask for one. "
        "Add-column data_type is text, numeric, integer, boolean, date, timestamptz, or list. "
        "These are the ONLY routes. Any other path (for example /v1/layouts, /v1/container-types, "
        "/v1/relations) does not exist; use the routes below exactly, with these body field names "
        "(display_name, not name or label, for tables and columns):\n"
        + route_formats_text()
        + "\nUse ids from the catalog below for table_id, list_id, role_id, column ids and sample type ids. "
        "For a table or column created by an earlier step in this run, put its display_name in table_id "
        "and add that step to depends_on; it is resolved at apply time. "
        "Before proposing anything, check the catalog: if a table, column, list, entry, role, or container "
        "type already exists, do not propose it again. "
        "Sample types and matrices are entries in the existing sample_types and matrix_types lists: "
        "add a missing one with POST /lists/sample_types/entries or POST /lists/matrix_types/entries. "
        "Never propose a new table for sample types, matrices, or container types. "
        "Never invent values the excerpts do not give. Kit lot numbers, part numbers, expiry dates, and serials "
        "are recorded per run, not configured: do not create lists, entries or columns for them (on any table); "
        "such a column proposal is stopped. Use reagent tracking instead: for each kit or reagent the excerpts "
        "name, add the reagent (vendor-agnostic) with POST /v1/reagents, its supplier with POST /v1/vendors, and "
        "the vendor's catalog number with POST /v1/reagent-vendors (reagent and vendor by name or id; "
        "catalog_number, unit and reorder fields only when the excerpts give them; add the reagent and vendor "
        "steps to depends_on). Reuse a vendor or reagent already in the catalog. Lots and the lot used on a run are recorded at the bench "
        "(POST /v1/reagent-lots, POST /v1/reagent-uses): do not call those routes. "
        "Instruments the excerpts name go on the catalog with POST /v1/instruments "
        "(instrument type from the instrument_types list, vendor by name or id, model and serial only when given). "
        "Do not set maintenance_tracked. An Administrator can turn on maintenance tracking. "
        "Types are a plain list with no maintenance setting. Never propose maintenance schedules, "
        "due dates, events or downtime. "
        "Maintenance events, downtime and instrument use are bench records "
        "(POST /v1/instrument-maintenance-events, POST /v1/instrument-downtime, POST /v1/instrument-uses): "
        "do not call those routes. "
        "A cutoff or acceptance limit in the excerpts is example data from the SOP; do not configure it as a value. "
        "Only tables marked 'new columns OK' take new columns; experiments, tests, results and containers do not. "
        "A measured result (for example a Qubit concentration in ng/uL) is an analyte on an analysis, recorded "
        "on the sample's test: POST /analytes (units_default by unit name or id), POST /analyses (method required), "
        "then POST /analyses/{analysis name or id}/analytes with analyte_ids (names of analytes created earlier "
        "are allowed; add those steps to depends_on). The experiment template is the process, not the result fields. "
        "If something the excerpts need already exists (same or nearly the same name, e.g. 'K2EDTA Tube (5mL)' for "
        "an EDTA tube, or the same template under another name), reuse it: do not create a near-duplicate. "
        "If it already exists exactly, still send its normal call (the server shows it as No change); "
        "never write a gap for something that already exists."
        + ("\n\nCatalog for this lab:\n" + catalog if catalog else "")
    )


def _user_prompt(chunks: list[str], goal_note: str | None, feedback: str | None) -> str:
    parts = []
    if goal_note:
        parts.append(f"Goal: {goal_note}")
    if feedback:
        parts.append(f"Redo this step. Feedback: {feedback}. Return one step.")
    if chunks:
        parts.append("File excerpts:\n" + "\n---\n".join(chunks))
    else:
        parts.append("No file excerpts.")
    return "\n\n".join(parts)


def _http_reason(exc: Exception) -> str:
    """A short, key-free reason for a failed model call (UAT: 'failed' with no why)."""
    if isinstance(exc, httpx.TimeoutException):
        return f"timed out after {int(model_timeout())} s (CONFIGURING_AGENT_TIMEOUT_S)"
    if isinstance(exc, httpx.ConnectError):
        return "could not connect"
    return type(exc).__name__


def _status_reason(response) -> str:
    detail = ""
    try:
        body = response.json()
        err = body.get("error") if isinstance(body, dict) else None
        detail = (err.get("message") if isinstance(err, dict) else err) or ""
    except Exception:  # noqa: BLE001 - non-JSON error body
        detail = ""
    detail = str(detail).strip()[:200]
    return f"HTTP {response.status_code}" + (f": {detail}" if detail else "")


def _get_json(url: str, headers: dict[str, str], params: dict | None = None) -> dict:
    try:
        response = httpx.get(url, headers=headers, params=params, timeout=30.0)
    except httpx.HTTPError as exc:
        raise ProviderError("Couldn't load models — check key or try again") from exc
    if response.status_code >= 400:
        raise ProviderError("Couldn't load models — check key or try again")
    return response.json()


def _openai_compatible(url: str, model: str, api_key: str, system: str, user: str) -> str:
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=model_timeout(),
        )
    except httpx.HTTPError as exc:
        raise ProviderError(f"The {url} call failed: {_http_reason(exc)}.") from exc
    if response.status_code >= 400:
        raise ProviderError(f"The model call failed ({_status_reason(response)}). Check the key and the model.")
    try:
        choice = response.json()["choices"][0]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise BadReply("The model reply had no choices.") from exc
    if choice.get("finish_reason") == "length":
        raise BadReply("The model reply was cut off (finish_reason length).")
    content = (choice.get("message") or {}).get("content")
    if isinstance(content, list):  # content parts
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    if not content:
        raise BadReply("The model reply was empty.")
    return content


def _anthropic(model: str, api_key: str, system: str, user: str) -> str:
    try:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 8192,
                "temperature": 0,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=model_timeout(),
        )
    except httpx.HTTPError as exc:
        raise ProviderError(f"The Anthropic call failed: {_http_reason(exc)}.") from exc
    if response.status_code >= 400:
        raise ProviderError(f"The model call failed ({_status_reason(response)}). Check the key and the model.")
    data = response.json()
    if data.get("stop_reason") == "max_tokens":
        raise BadReply("The model reply was cut off (max_tokens).")
    parts = [block.get("text", "") for block in data.get("content") or [] if block.get("type") == "text"]
    return "\n".join(parts)


def _parse_json(text: str) -> dict[str, Any]:
    """The configuration object in a reply. Accepts a bare object, a fenced
    block anywhere, or an object with prose around it (first balanced one
    that decodes to an object with "steps")."""
    raw = (text or "").strip()
    if not raw:
        raise BadReply("The model reply was empty.")
    decoder = json.JSONDecoder()
    starts = [i for i, ch in enumerate(raw) if ch == "{"]
    for start in starts:
        try:
            parsed, _end = decoder.raw_decode(raw, start)
        except json.JSONDecodeError:
            continue
        # A nested object of a truncated reply (a step's body) is not the answer.
        if isinstance(parsed, dict) and "steps" in parsed:
            return parsed
        # A bare refusal or single row ({"gap": ...}) is the answer only when it
        # is the outermost object; an inner one is part of a cut-off reply.
        if start == starts[0] and isinstance(parsed, dict) and (
            set(parsed) & {"target", "gap", "reason", "refusal"}
        ):
            return parsed
    reason = "cut off" if starts else "no JSON object"
    raise BadReply(f"The model did not return configuration JSON ({reason}; {len(raw)} chars).")
