"""Фабрика LLM-клиентов: OpenAI-совместимый эндпоинт или GigaChat.

Способы подключения (по приоритету):
1. GigaChat (Сбер) — задан `GIGACHAT_AUTH_KEY`. Выбран для демо, потому что
   у него бесплатный тариф и он хорошо пишет по-русски. Его chat/completions
   совместим с OpenAI-схемой, но вместо постоянного ключа — OAuth-токен со
   сроком жизни ~30 минут, поэтому токен кэшируется и обновляется прозрачно
   (httpx.Auth ниже).
2. Любой OpenAI-совместимый эндпоинт — `LLM_BASE_URL` / `LLM_API_KEY` /
   `LLM_MODEL` (см. .env.example).
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable

import httpx

GIGACHAT_BASE_URL = "https://gigachat.devices.sberbank.ru/api/v1"
GIGACHAT_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"


def _fetch_gigachat_token(auth_key: str, scope: str) -> tuple[str, float]:
    """Обменивает авторизационный ключ на access-токен.

    Возвращает (токен, unix-время истечения в секундах).
    verify=False: цепочка сертификатов Сбера подписана НУЦ Минцифры,
    которого нет в системных хранилищах вне РФ (в т.ч. на HF Spaces).
    """
    resp = httpx.post(
        GIGACHAT_OAUTH_URL,
        headers={
            "Authorization": f"Basic {auth_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"scope": scope},
        verify=False,
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    return payload["access_token"], payload["expires_at"] / 1000  # мс -> с


class GigaChatTokenManager:
    """Кэширует OAuth-токен и обновляет его за `margin` секунд до истечения."""

    def __init__(
        self,
        auth_key: str,
        scope: str = "GIGACHAT_API_PERS",
        fetch: Callable[[str, str], tuple[str, float]] = _fetch_gigachat_token,
        margin: float = 60.0,
    ) -> None:
        self._auth_key = auth_key
        self._scope = scope
        self._fetch = fetch
        self._margin = margin
        self._token: str | None = None
        self._expires_at = 0.0

    def token(self) -> str:
        if self._token is None or time.time() >= self._expires_at - self._margin:
            self._token, self._expires_at = self._fetch(self._auth_key, self._scope)
        return self._token


class _BearerAuth(httpx.Auth):
    def __init__(self, manager: GigaChatTokenManager) -> None:
        self._manager = manager

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self._manager.token()}"
        yield request


def make_client():
    """OpenAI-совместимый клиент по переменным окружения (см. модуль)."""
    from openai import OpenAI  # ленивый импорт: тесты не требуют ключей

    giga_key = os.getenv("GIGACHAT_AUTH_KEY")
    if giga_key:
        manager = GigaChatTokenManager(giga_key, os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"))
        return OpenAI(
            base_url=GIGACHAT_BASE_URL,
            api_key="unused",  # реальный токен подставляет _BearerAuth
            http_client=httpx.Client(verify=False, auth=_BearerAuth(manager), timeout=60),
        )
    return OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY"))


def default_model() -> str:
    if os.getenv("GIGACHAT_AUTH_KEY"):
        return os.getenv("GIGACHAT_MODEL", "GigaChat")
    return os.getenv("LLM_MODEL", "gpt-4o-mini")


def llm_configured() -> bool:
    return bool(os.getenv("GIGACHAT_AUTH_KEY") or os.getenv("LLM_API_KEY"))
