"""One provider per run. Models come from that provider's live list. No fixed catalog."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.services.configuring_agent_allow import PROVIDERS, schema_table_names
from app.services.ui_schema_catalog import NOT_SCHEMA_TABLES

OPENAI_MODELS = "https://api.openai.com/v1/models"
XAI_MODELS = "https://api.x.ai/v1/models"
ANTHROPIC_MODELS = "https://api.anthropic.com/v1/models"
ANTHROPIC_VERSION = "2023-06-01"


class ProviderError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


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


def propose(provider: str, model: str, api_key: str, *, chunks: list[str], goal_note: str | None, feedback: str | None = None) -> dict[str, Any]:
    """Ask the stored provider and model for configuration steps. Returns parsed JSON."""
    if provider not in PROVIDERS:
        raise ProviderError(f"Provider must be one of: {', '.join(PROVIDERS)}.")
    if not model:
        raise ProviderError("No model is selected.")
    system = _system_prompt()
    user = _user_prompt(chunks, goal_note, feedback)
    if provider == "anthropic":
        text = _anthropic(model, api_key, system, user)
    else:
        url = "https://api.openai.com/v1/chat/completions" if provider == "openai" else "https://api.x.ai/v1/chat/completions"
        text = _openai_compatible(url, model, api_key, system, user)
    return _parse_json(text)


def _system_prompt() -> str:
    names = schema_table_names()
    hidden = ", ".join(names["not_schema"])
    return (
        "You propose NimbleLIMS configuration. Reply with JSON only, no markdown. "
        "Shape: {\"steps\":[{\"group\":\"schema_tables|schema_columns|layouts|privileges|relations|other\","
        "\"target\":\"...\",\"action\":\"...\",\"why\":\"one line\","
        "\"call\":{\"method\":\"POST\",\"path\":\"/v1/schema/columns\",\"body\":{}}}]} "
        "If no existing API can express a step, that step has \"gap\" (plain words) and no call. "
        "Do not invent a workaround. Do not continue past a gap. "
        "Follow the lab process in the file excerpts. Do not assume every lab uses the same method. "
        "Do not invent needs the excerpts do not state. "
        f"Schema lab tables: {', '.join(names['lab'])}. "
        f"Schema system tables (browse only, no new columns): {', '.join(names['system'])}. "
        f"Not schema tables: {hidden}. Do not add columns on {', '.join(sorted(NOT_SCHEMA_TABLES))}. "
        "List values use POST /lists and POST /lists/{name}/entries, group other. "
        "Relations are one_to_many or one_to_one on an existing foreign key. Never many_to_many. "
        "Do not call asked-for, routing, ELN process definitions, parsers, results, custom fields, "
        "workflow templates, or receive. Do not grant schema:edit. Do not create users. "
        "Experiment templates may be created with POST /v1/experiment-templates when the excerpts ask for one. "
        "Add-column data_type is text, numeric, integer, boolean, date, timestamptz, or list."
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
            timeout=90.0,
        )
    except httpx.HTTPError as exc:
        raise ProviderError(f"The {url} call failed.") from exc
    if response.status_code >= 400:
        raise ProviderError("The model call failed. Check the key and the model.")
    data = response.json()
    return data["choices"][0]["message"]["content"]


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
                "max_tokens": 4096,
                "temperature": 0,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=90.0,
        )
    except httpx.HTTPError as exc:
        raise ProviderError("The Anthropic call failed.") from exc
    if response.status_code >= 400:
        raise ProviderError("The model call failed. Check the key and the model.")
    data = response.json()
    parts = [block.get("text", "") for block in data.get("content") or [] if block.get("type") == "text"]
    return "\n".join(parts)


def _parse_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError("The model did not return configuration JSON.") from exc
    if not isinstance(parsed, dict):
        raise ProviderError("The model did not return configuration JSON.")
    return parsed
