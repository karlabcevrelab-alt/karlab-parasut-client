"""Paraşüt purchase_bills çekme + normalize etme.

Sayfalama ve genel filtreler burada; hangi faturanın "ödenmeye uygun"
olduğu, hangi IBAN'ın "onaylı" sayıldığı gibi domain kararları BURADA
DEĞİL — tüketici uygulamada.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, AsyncIterator, Optional

from .client import ParasutClient
from .models import NormalizedPurchaseBill, normalize_currency

DEFAULT_PAGE_SIZE = 25


def _parse_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal("0")


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value)


def _map_bill(item: dict, contacts_by_id: dict[str, dict]) -> NormalizedPurchaseBill:
    attrs = item.get("attributes", {})

    supplier_rel = (
        item.get("relationships", {}).get("supplier", {}).get("data")
    )
    contact = contacts_by_id.get(supplier_rel["id"]) if supplier_rel else None
    contact_attrs = (contact or {}).get("attributes", {})

    return NormalizedPurchaseBill(
        parasut_id=str(item["id"]),
        supplier_parasut_id=supplier_rel["id"] if supplier_rel else None,
        supplier_name=(
            contact_attrs.get("name") or contact_attrs.get("short_name") or ""
        ),
        supplier_tax_no=contact_attrs.get("tax_number"),
        supplier_iban=contact_attrs.get("iban"),
        invoice_no=attrs.get("invoice_no") or attrs.get("invoice_id"),
        issue_date=_parse_date(attrs.get("issue_date")),
        due_date=_parse_date(attrs.get("due_date")) or _parse_date(attrs.get("issue_date")),
        net_total=_parse_decimal(attrs.get("net_total")),
        remaining=_parse_decimal(attrs.get("remaining", attrs.get("net_total"))),
        total_paid=_parse_decimal(attrs.get("total_paid")),
        currency=normalize_currency(attrs.get("currency")),
        archived=bool(attrs.get("archived")),
        raw=attrs,
    )


async def fetch_purchase_bills(
    client: ParasutClient,
    *,
    since: Optional[date] = None,
    extra_filters: Optional[dict[str, str]] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = 50,
) -> AsyncIterator[NormalizedPurchaseBill]:
    """Paraşüt'ten purchase_bills'i sayfalayarak çeker, normalize edip
    tek tek yield eder.

    `since` verilirse `filter[issue_date][gteq]` uygulanır. `extra_filters`
    ile ek Ransack-tarzı filtreler eklenebilir (örn.
    `{"filter[remaining][gt]": "0"}`) — Paraşüt filtre söz dizimi
    `filter[alan][operator]=değer` şeklindedir, ham `filter[alan]=X..`
    aralık söz dizimi GEÇERSİZDİR (bu oturumda bulunan bir hata).
    """
    page = 1
    while page <= max_pages:
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": page_size,
            "include": "supplier",
            "sort": "-issue_date",
        }
        if since:
            params["filter[issue_date][gteq]"] = since.isoformat()
        if extra_filters:
            params.update(extra_filters)

        payload = await client.get("/purchase_bills", params=params)
        data = payload.get("data", [])
        if not data:
            return

        contacts_by_id = {
            inc["id"]: inc
            for inc in payload.get("included", [])
            if inc.get("type") == "contacts"
        }

        for item in data:
            yield _map_bill(item, contacts_by_id)

        page += 1
