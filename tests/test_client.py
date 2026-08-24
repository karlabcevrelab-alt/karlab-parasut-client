import httpx
import pytest
import respx

from karlab_parasut_client.client import ParasutAuthError, ParasutClient


def make_client() -> ParasutClient:
    return ParasutClient(
        client_id="cid",
        client_secret="secret",
        email="a@b.com",
        password="pw",
        company_id="297985",
    )


def test_is_configured():
    assert make_client().is_configured() is True
    assert ParasutClient(
        client_id="", client_secret="s", email="e", password="p", company_id="c"
    ).is_configured() is False


@pytest.mark.asyncio
@respx.mock
async def test_get_token_fetches_and_caches():
    route = respx.post("https://api.parasut.com/oauth/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok123", "expires_in": 7200})
    )
    client = make_client()

    token1 = await client.get_token()
    token2 = await client.get_token()

    assert token1 == "tok123"
    assert token2 == "tok123"
    assert route.call_count == 1  # ikinci çağrı cache'ten geldi


@pytest.mark.asyncio
@respx.mock
async def test_get_token_raises_on_auth_failure():
    respx.post("https://api.parasut.com/oauth/token").mock(
        return_value=httpx.Response(401, json={"error": "invalid_grant"})
    )
    client = make_client()

    with pytest.raises(ParasutAuthError):
        await client.get_token()


@pytest.mark.asyncio
@respx.mock
async def test_get_retries_429_then_succeeds():
    respx.post("https://api.parasut.com/oauth/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok123", "expires_in": 7200})
    )
    route = respx.get("https://api.parasut.com/v4/297985/purchase_bills").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"data": []}),
        ]
    )
    client = make_client()

    result = await client.get("/purchase_bills")

    assert result == {"data": []}
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_post_sends_authenticated_request():
    respx.post("https://api.parasut.com/oauth/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok123", "expires_in": 7200})
    )
    route = respx.post("https://api.parasut.com/v4/297985/purchase_bills/42/payments").mock(
        return_value=httpx.Response(201, json={"data": {"id": "999"}})
    )
    client = make_client()

    result = await client.post("/purchase_bills/42/payments", json_body={"data": {"type": "payments"}})

    assert result == {"data": {"id": "999"}}
    sent_request = route.calls[0].request
    assert sent_request.headers["Authorization"] == "Bearer tok123"
