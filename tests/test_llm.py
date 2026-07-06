"""Тесты фабрики LLM-клиентов и кэша OAuth-токена GigaChat — без сети."""

import time

from classic_rag.llm import GIGACHAT_BASE_URL, GigaChatTokenManager, default_model, make_client


def make_fetcher(calls: list, ttl: float):
    def fetch(auth_key: str, scope: str) -> tuple[str, float]:
        calls.append((auth_key, scope))
        return f"token-{len(calls)}", time.time() + ttl

    return fetch


def test_token_cached_until_expiry() -> None:
    calls: list = []
    mgr = GigaChatTokenManager("key", fetch=make_fetcher(calls, ttl=3600))
    assert mgr.token() == "token-1"
    assert mgr.token() == "token-1"  # повторный вызов — из кэша
    assert len(calls) == 1
    assert calls[0] == ("key", "GIGACHAT_API_PERS")


def test_token_refreshed_within_margin() -> None:
    calls: list = []
    # токен «истекает» через 10 с — при margin=60 он уже считается протухшим
    mgr = GigaChatTokenManager("key", fetch=make_fetcher(calls, ttl=10), margin=60)
    assert mgr.token() == "token-1"
    assert mgr.token() == "token-2"
    assert len(calls) == 2


def test_make_client_prefers_gigachat(monkeypatch) -> None:
    monkeypatch.setenv("GIGACHAT_AUTH_KEY", "abc")
    client = make_client()
    assert str(client.base_url).startswith(GIGACHAT_BASE_URL)
    assert default_model() == "GigaChat"


def test_make_client_generic_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("GIGACHAT_AUTH_KEY", raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_MODEL", "m")
    client = make_client()
    assert str(client.base_url).startswith("https://example.com/v1")
    assert default_model() == "m"
