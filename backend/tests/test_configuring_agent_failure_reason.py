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
