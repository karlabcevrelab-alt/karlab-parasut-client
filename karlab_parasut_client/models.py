"""Paraşüt purchase_bill için normalize edilmiş, doğrulanmış veri modeli.

DİKKAT — alan anlamları Paraşüt'ün kendi API'sinde İngilizce'deki alışılmış
"net/gross" anlamının TERSİ (2026-08-24'te ham veriyle doğrulandı):
  - net_total       = VAT DAHİL nihai tutar (indirimden sonra)
  - gross_total     = VAT HARİÇ tutar (before_taxes_total ile aynı)
  - remaining       = ödenmemiş faturada net_total ile aynı

Bu modül SADECE veri şekli tanımlar — HTTP, DB, domain mantığı burada YOK.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional


@dataclass(frozen=True)
class NormalizedPurchaseBill:
    """Bir Paraşüt purchase_bill kaydının normalize edilmiş görünümü.

    Tüketici uygulamalar bu tipin alanlarına göre kendi DB modellerini
    doldurur — hangi alanın hangi iş anlamına geldiğine dair yorum bu
    kütüphanenin dışına taşınmaz.
    """

    parasut_id: str
    supplier_name: str
    supplier_tax_no: Optional[str]
    supplier_iban: Optional[str]
    invoice_no: Optional[str]
    issue_date: Optional[date]
    due_date: Optional[date]

    net_total: Decimal
    """Paraşüt'ün net_total alanı — VAT DAHİL nihai tutar. 'amount' gibi
    belirsiz bir isim kasıtlı olarak kullanılmadı (bkz. README)."""

    remaining: Decimal
    """Paraşüt'ün remaining alanı — kalan/ödenecek bakiye."""

    total_paid: Decimal
    currency: str
    """Normalize edilmiş ISO kod (Paraşüt'ün 'TRL' değeri 'TRY'ye çevrilir)."""

    archived: bool

    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    """Ham `attributes` sözlüğü — ileride ihtiyaç olursa, ama normal akışta
    kullanılmamalı (yeni bir alan gerekiyorsa modele eklenmeli, raw'dan
    okunmamalı — aksi halde bu kütüphanenin varlık sebebi ortadan kalkar)."""


_CURRENCY_MAP = {"TRL": "TRY"}


def normalize_currency(raw_currency: Optional[str]) -> str:
    code = (raw_currency or "TRY").upper()
    return _CURRENCY_MAP.get(code, code)
