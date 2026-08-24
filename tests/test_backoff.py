import httpx
import pytest

from karlab_parasut_client.backoff import RateLimitExceeded, request_with_backoff


@pytest.mark.asyncio
async def test_returns_immediately_on_non_429():
    calls = []

    async def send():
        calls.append(1)
        return httpx.Response(200, json={"ok": True})

    response = await request_with_backoff(send)
    assert response.status_code == 200
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds():
    calls = []

    async def send():
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True})

    response = await request_with_backoff(send, fallback_wait_seconds=0)
    assert response.status_code == 200
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_raises_after_max_attempts():
    async def send():
        return httpx.Response(429, headers={"Retry-After": "0"})

    with pytest.raises(RateLimitExceeded):
        await request_with_backoff(send, max_attempts=2, fallback_wait_seconds=0)
