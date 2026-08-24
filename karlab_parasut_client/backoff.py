"""429 (rate limit) için Retry-After'a saygılı backoff.

Domain mantığı yok — sadece "bu isteği ne zaman tekrar dene" kararı.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

import httpx

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 4
DEFAULT_FALLBACK_WAIT_SECONDS = 2.0


class RateLimitExceeded(Exception):
    """max_attempts denemesinden sonra hâlâ 429 alınıyorsa fırlatılır."""


async def request_with_backoff(
    send: Callable[[], Awaitable[httpx.Response]],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    fallback_wait_seconds: float = DEFAULT_FALLBACK_WAIT_SECONDS,
) -> httpx.Response:
    """`send()` çağırır; 429 dönerse Retry-After (yoksa üstel fallback) kadar
    bekleyip tekrar dener. 429 dışındaki durumlarda ilk yanıtı olduğu gibi
    döner — status kontrolü (raise_for_status vb.) çağıranın işidir.
    """
    last_response: httpx.Response | None = None
    for attempt in range(max_attempts):
        response = await send()
        if response.status_code != 429:
            return response
        last_response = response
        retry_after = response.headers.get("Retry-After")
        wait_seconds = (
            float(retry_after)
            if retry_after is not None
            else fallback_wait_seconds * (attempt + 1)
        )
        await asyncio.sleep(wait_seconds)

    assert last_response is not None
    raise RateLimitExceeded(
        f"{max_attempts} denemeden sonra hâlâ 429 alınıyor (son Retry-After: "
        f"{last_response.headers.get('Retry-After')!r})"
    )
