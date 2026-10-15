"""SOP parse uses the configuring agent's provider selection and client.

Provider calls are mocked at httpx; no network.
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.services import sop_parse_service as sps
from app.services.configuring_agent_crypto import encrypt_secret

KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "SOP_PARSE_PROVIDER", "SOP_PARSE_MODEL")
RESULT = {"template_definition": {"experiment_name": "x"}, "parser_config": {}, "worklist_config": {}}


@pytest.fixture
def clean_env(monkeypatch):
    for k in KEYS:
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def _settings(provider=None, model=None, key=None):
    return SimpleNamespace(agent_provider=provider, agent_model=model,
                           key_ciphertext=encrypt_secret(key) if key else None)


def _reply(provider):
    r = MagicMock(status_code=200)
    text = json.dumps(RESULT)
    if provider == "anthropic":
        r.json.return_value = {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}
    else:
        r.json.return_value = {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}
    return r


URLS = {
    "anthropic": "https://api.anthropic.com/v1/messages",
    "openai": "https://api.openai.com/v1/chat/completions",
    "xai": "https://api.x.ai/v1/chat/completions",
}
ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "xai": "XAI_API_KEY"}


# ── selection ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("provider", ["anthropic", "openai", "xai"])
def test_stored_settings_pick_provider_model_and_key(clean_env, provider):
    assert sps.resolve_sop_parse_llm(_settings(provider, "m-1", "stored-key")) == (provider, "m-1", "stored-key")


@pytest.mark.parametrize("provider", ["anthropic", "openai", "xai"])
def test_stored_provider_without_stored_key_uses_only_its_env_var(clean_env, provider):
    for p, name in ENV.items():
        clean_env.setenv(name, f"env-{p}")
    assert sps.resolve_sop_parse_llm(_settings(provider, "m-1")) == (provider, "m-1", f"env-{provider}")


@pytest.mark.parametrize("provider", ["anthropic", "openai", "xai"])
def test_whichever_env_key_is_set_is_used(clean_env, provider):
    clean_env.setenv(ENV[provider], "k")
    assert sps.resolve_sop_parse_llm(None) == (provider, sps.DEFAULT_MODELS[provider], "k")


def test_env_order_and_overrides(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "o")
    clean_env.setenv("XAI_API_KEY", "x")
    assert sps.resolve_sop_parse_llm(None)[0] == "openai"
    clean_env.setenv("SOP_PARSE_PROVIDER", "xai")
    clean_env.setenv("SOP_PARSE_MODEL", "grok-custom")
    assert sps.resolve_sop_parse_llm(None) == ("xai", "grok-custom", "x")


def test_settings_provider_without_model_uses_that_provider_default(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "o")
    clean_env.setenv("XAI_API_KEY", "x")
    assert sps.resolve_sop_parse_llm(_settings("openai", None)) == ("openai", sps.DEFAULT_MODELS["openai"], "o")


@pytest.mark.parametrize("provider", ["anthropic", "openai", "xai"])
@pytest.mark.parametrize("model", [None, "m-1"])
def test_configured_provider_never_falls_through_to_another_env_key(clean_env, provider, model):
    """UAT 9d0108f: provider set, key cleared, model null fell through to XAI_API_KEY."""
    for p, name in ENV.items():
        if p != provider:
            clean_env.setenv(name, f"env-{p}")
    with pytest.raises(sps.NoProviderKey) as exc:
        sps.resolve_sop_parse_llm(_settings(provider, model))
    msg = str(exc.value)
    assert msg.startswith(f"No key configured for {provider}.")
    assert ENV[provider] in msg
    assert "env-" not in msg


# ── no key ───────────────────────────────────────────────────────────────────

def test_no_key_message(clean_env):
    with pytest.raises(sps.NoProviderKey) as exc:
        sps.resolve_sop_parse_llm(None)
    msg = str(exc.value)
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "Configuring agent settings"):
        assert name in msg


def test_chosen_provider_without_key_names_its_variable(clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "a")  # another vendor's key is not used
    with pytest.raises(sps.NoProviderKey) as exc:
        sps.resolve_sop_parse_llm(_settings("xai", "grok-4"))
    assert "XAI_API_KEY" in str(exc.value)


def test_bad_sop_parse_provider(clean_env):
    clean_env.setenv("SOP_PARSE_PROVIDER", "other")
    with pytest.raises(sps.NoProviderKey, match="SOP_PARSE_PROVIDER"):
        sps.resolve_sop_parse_llm(None)


# ── full background run (real DB, mocked HTTP) ───────────────────────────────

def _seed(db_engine):
    from app.repositories.flexible_experiment_repository import SopParseJobRepository
    db = sessionmaker(bind=db_engine)()
    try:
        job = SopParseJobRepository(db).create(sop_filename="s.txt", instrument_filename="i.csv", created_by=None)
        db.commit()
        return job.id
    finally:
        db.close()


def _job(db_engine, job_id):
    from app.repositories.flexible_experiment_repository import SopParseJobRepository
    db = sessionmaker(bind=db_engine)()
    try:
        j = SopParseJobRepository(db).get_by_id(job_id)
        return j.status.value, j.result, j.error_message
    finally:
        db.close()


def _run(db_engine, job_id):
    sps.SOPParseService.run_extraction_background(
        job_id=job_id, sop_text="SOP", instrument_text="a,b", user_id=uuid4(),
        session_factory=sessionmaker(bind=db_engine))


@pytest.mark.parametrize("provider", ["anthropic", "openai", "xai"])
def test_parse_runs_on_each_provider(db_engine, clean_env, provider):
    clean_env.setenv(ENV[provider], "secret-key")
    job_id = _seed(db_engine)
    with patch.object(sps, "_read_agent_settings", return_value=None), \
         patch("app.services.configuring_agent_llm.httpx.post", return_value=_reply(provider)) as post:
        _run(db_engine, job_id)
    url = post.call_args.args[0]
    headers = post.call_args.kwargs["headers"]
    assert url == URLS[provider]
    assert "secret-key" in (headers.get("x-api-key") or headers.get("Authorization"))
    assert post.call_args.kwargs["json"]["model"] == sps.DEFAULT_MODELS[provider]
    status, result, err = _job(db_engine, job_id)
    assert (status, err) == ("complete", None)
    assert result["template_definition"]["experiment_name"] == "x"


def test_parse_uses_stored_configuring_agent_settings(db_engine, clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "not-this-one")
    job_id = _seed(db_engine)
    stored = {"agent_provider": "xai", "agent_model": "grok-4.7", "key_ciphertext": encrypt_secret("xk")}
    with patch.object(sps, "_read_agent_settings", return_value=stored), \
         patch("app.services.configuring_agent_llm.httpx.post", return_value=_reply("xai")) as post:
        _run(db_engine, job_id)
    assert post.call_args.args[0] == URLS["xai"]
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer xk"
    assert post.call_args.kwargs["json"]["model"] == "grok-4.7"
    assert _job(db_engine, job_id)[0] == "complete"


def test_parse_with_no_key_fails_with_clear_message(db_engine, clean_env):
    job_id = _seed(db_engine)
    with patch.object(sps, "_read_agent_settings", return_value=None), \
         patch("app.services.configuring_agent_llm.httpx.post") as post:
        _run(db_engine, job_id)
    post.assert_not_called()
    status, _, err = _job(db_engine, job_id)
    assert status == "failed"
    assert err == sps.NO_KEY_MESSAGE


def test_provider_http_error_is_redacted(db_engine, clean_env):
    clean_env.setenv("XAI_API_KEY", "secret-key")
    job_id = _seed(db_engine)
    bad = MagicMock(status_code=404)
    bad.json.return_value = {"error": "Model not found for team 9b1c2d3e4f5a"}
    with patch.object(sps, "_read_agent_settings", return_value=None), \
         patch("app.services.configuring_agent_llm.httpx.post", return_value=bad):
        _run(db_engine, job_id)
    status, _, err = _job(db_engine, job_id)
    assert status == "failed"
    assert err.startswith("AI provider error (xai)")
    assert "HTTP 404" in err
    assert "9b1c2d3e4f5a" not in err and "secret-key" not in err


def test_settings_are_read_in_the_background_session(db_engine, clean_env):
    """The real settings reader runs in session 1 and feeds selection."""
    clean_env.setenv("OPENAI_API_KEY", "ok")
    job_id = _seed(db_engine)
    with patch.object(sps, "_read_agent_settings", wraps=sps._read_agent_settings) as reader, \
         patch.object(sps, "resolve_sop_parse_llm", return_value=("openai", "m", "ok")) as resolve, \
         patch("app.services.configuring_agent_llm.httpx.post", return_value=_reply("openai")):
        _run(db_engine, job_id)
    reader.assert_called_once()
    resolve.assert_called_once()
    assert _job(db_engine, job_id)[0] == "complete"
