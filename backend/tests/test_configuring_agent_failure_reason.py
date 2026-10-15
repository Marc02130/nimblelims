"""UAT: the first R1 run ended 'failed' with only "The ... call failed."
(a 300 s timeout). Every failure path must say why."""
import httpx
import pytest

from app.services import configuring_agent_llm as llm


def _raise(exc):
    def post(*a, **k):
        raise exc
    return post


@pytest.mark.parametrize("exc,needle", [
    (httpx.ReadTimeout("slow"), "timed out after"),
    (httpx.ConnectError("no route"), "could not connect"),
    (httpx.RemoteProtocolError("bye"), "RemoteProtocolError"),
])
def test_transport_failures_name_the_reason(monkeypatch, exc, needle):
    monkeypatch.setattr(llm.httpx, "post", _raise(exc))
    for call in (lambda: llm._openai_compatible("https://api.x.ai/v1/chat/completions", "m", "k", "s", "u"),
                 lambda: llm._anthropic("m", "k", "s", "u")):
        with pytest.raises(llm.ProviderError) as err:
            call()
        assert needle in err.value.message and "k" != err.value.message


def test_http_error_includes_status_and_provider_message(monkeypatch):
    resp = httpx.Response(429, json={"error": {"message": "rate limited"}})
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: resp)
    with pytest.raises(llm.ProviderError) as err:
        llm._openai_compatible("https://x/v1/chat/completions", "m", "secret-key", "s", "u")
    assert "HTTP 429" in err.value.message and "rate limited" in err.value.message
    assert "secret-key" not in err.value.message


TEAM = "7350d961-17a6-48ab-aab4-88b770452354"


def test_provider_404_redacts_the_team_id(monkeypatch):
    """UAT 67481e9: the xAI 404 message showed the team id."""
    msg = (f"The model grok-nope does not exist or your team {TEAM} does not have access to it. "
           "If you believe this is a mistake, please contact support.")
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: httpx.Response(404, json={"error": msg}))
    with pytest.raises(llm.ProviderError) as err:
        llm._openai_compatible("https://api.x.ai/v1/chat/completions", "grok-nope", "k", "s", "u")
    assert TEAM not in err.value.message
    assert "HTTP 404" in err.value.message and "your team [redacted]" in err.value.message


@pytest.mark.parametrize("raw,secret", [
    ("organization org-AbCdEf123456 is over quota", "org-AbCdEf123456"),
    ("project proj_abc12345 not found", "proj_abc12345"),
    ("account id: 99881234 suspended", "99881234"),
])
def test_org_project_account_ids_are_redacted(raw, secret):
    assert secret not in llm.ProviderError(raw).message


def test_plain_words_after_team_are_kept():
    assert llm.redact_ids("Check the team settings and organization billing") == \
        "Check the team settings and organization billing"
