"""Paraşüt OAuth2 (Resource Owner Password Credentials) client.

Sadece kimlik doğrulama + genel authenticated GET. purchase_bills'e özel
mantık purchase_bills.py'de.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from .backoff import request_with_backoff

DEFAULT_BASE_URL = "https://api.parasut.com/v4"
DEFAULT_AUTH_URL = "https://api.parasut.com/oauth/token"

# Paraşüt access token'ları tipik olarak 2 saat geçerli; erken yenilemek
# için birkaç dakika pay bırakıyoruz.
_TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS = 120


class ParasutAuthError(Exception):
    pass


class ParasutClient:
    """Tek bir Paraşüt hesabı için kimlik doğrulama + HTTP client.

    Thread-safe DEĞİLDİR — her sync sürecinin kendi instance'ını oluşturması
    beklenir (tüketici uygulamalar zaten böyle kullanıyor).
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        email: str,
        password: str,
        company_id: str,
        base_url: str = DEFAULT_BASE_URL,
        auth_url: str = DEFAULT_AUTH_URL,
        http_timeout_seconds: float = 30.0,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.email = email
        self.password = password
        self.company_id = company_id
        self.base_url = base_url.rstrip("/")
        self.auth_url = auth_url
        self.http_timeout_seconds = http_timeout_seconds

        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        return bool(
            self.client_id and self.client_secret and self.email
            and self.password and self.company_id
        )

    async def get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        async with httpx.AsyncClient(timeout=self.http_timeout_seconds) as http:
            response = await http.post(
                self.auth_url,
                json={
                    "grant_type": "password",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "username": self.email,
                    "password": self.password,
                },
            )
        if response.status_code != 200:
            raise ParasutAuthError(
                f"Paraşüt token alınamadı: HTTP {response.status_code} — {response.text[:300]}"
            )

        data = response.json()
        token = data.get("access_token")
        if not token:
            raise ParasutAuthError(f"Paraşüt yanıtında access_token yok: {data!r}")

        expires_in = float(data.get("expires_in", 7200))
        self._token = token
        self._token_expires_at = time.monotonic() + max(
            expires_in - _TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS, 60
        )
        return token

    async def get(self, path: str, *, params: Optional[dict[str, Any]] = None) -> dict:
        """`{base_url}/{company_id}{path}` adresine authenticated GET.

        429'da otomatik backoff/retry yapar (bkz. backoff.py). Diğer
        hata durumlarında `httpx.HTTPStatusError` fırlatır.
        """
        token = await self.get_token()
        url = f"{self.base_url}/{self.company_id}{path}"

        async def _send() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.http_timeout_seconds) as http:
                return await http.get(
                    url,
                    params=params or {},
                    headers={"Authorization": f"Bearer {token}"},
                )

        response = await request_with_backoff(_send)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, *, json_body: Optional[dict[str, Any]] = None) -> dict:
        """`{base_url}/{company_id}{path}` adresine authenticated POST.

        429'da otomatik backoff/retry yapar. Diğer hata durumlarında
        `httpx.HTTPStatusError` fırlatır.
        """
        token = await self.get_token()
        url = f"{self.base_url}/{self.company_id}{path}"

        async def _send() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.http_timeout_seconds) as http:
                return await http.post(
                    url,
                    json=json_body or {},
                    headers={"Authorization": f"Bearer {token}"},
                )

        response = await request_with_backoff(_send)
        response.raise_for_status()
        return response.json()
