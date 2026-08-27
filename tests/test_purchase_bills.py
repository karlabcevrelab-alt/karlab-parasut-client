import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from karlab_parasut_client.purchase_bills import fetch_purchase_bills

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "purchase_bills_page1.json").read_text()
)


@pytest.mark.asyncio
async def test_fetch_maps_and_normalizes_bills():
    client = AsyncMock()
    client.get.side_effect = [FIXTURE, {"data": []}]

    bills = [b async for b in fetch_purchase_bills(client)]

    assert len(bills) == 2

    mng = bills[0]
    assert mng.parasut_id == "122930389"
    assert mng.supplier_parasut_id == "9001"
    assert mng.supplier_name == "MNG KARGO YURTİÇİ VE YURTDIŞI TAŞIMACILIK A.Ş."
    assert mng.supplier_tax_no == "6080712084"
    assert mng.supplier_iban is None
    assert mng.net_total == Decimal("239.89")
    assert mng.remaining == Decimal("239.89")
    assert mng.currency == "TRY"  # TRL -> TRY normalize edildi
    assert mng.archived is False

    shell = bills[1]
    assert shell.supplier_iban == "TR280004600798888000008721"
    assert shell.net_total == Decimal("16524.5")


@pytest.mark.asyncio
async def test_fetch_stops_on_empty_page():
    client = AsyncMock()
    client.get.side_effect = [{"data": []}]

    bills = [b async for b in fetch_purchase_bills(client)]
    assert bills == []
    assert client.get.call_count == 1


@pytest.mark.asyncio
async def test_since_filter_is_applied():
    from datetime import date

    client = AsyncMock()
    client.get.side_effect = [{"data": []}]

    async for _ in fetch_purchase_bills(client, since=date(2026, 5, 1)):
        pass

    _, kwargs = client.get.call_args
    assert kwargs["params"]["filter[issue_date][gteq]"] == "2026-05-01"


@pytest.mark.asyncio
async def test_contactless_bill_exposes_description():
    """Paraşüt'te cari kart seçmeden, sadece fiş fotoğrafıyla girilen
    ("Gider Fişi") kayıtlarda relationships.supplier.data null gelir —
    supplier_name boş kalır. description alanı (insan tarafından girilen
    serbest metin, genellikle tedarikçi adı) tüketicilere expose edilmeli
    ki .raw'a inmeden fallback yapabilsinler (bkz. gerçek ÇEBİ Hukuk &
    Danışmanlık kaydı, parasut_id=124166041)."""
    page = {
        "data": [
            {
                "id": "124166041",
                "type": "purchase_bills",
                "attributes": {
                    "net_total": "24450.0",
                    "remaining": "24450.0",
                    "total_paid": "0.0",
                    "issue_date": "2026-08-27",
                    "due_date": "2026-08-31",
                    "description": "ÇEBİ Hukuk & Danışmanlık",
                    "archived": False,
                    "currency": "TRL",
                    "invoice_no": None,
                },
                "relationships": {"supplier": {"data": None}},
            }
        ]
    }
    client = AsyncMock()
    client.get.side_effect = [page, {"data": []}]

    bills = [b async for b in fetch_purchase_bills(client)]

    assert len(bills) == 1
    bill = bills[0]
    assert bill.supplier_name == ""
    assert bill.supplier_parasut_id is None
    assert bill.description == "ÇEBİ Hukuk & Danışmanlık"


@pytest.mark.asyncio
async def test_contactful_bill_description_still_available_but_unused_by_convention():
    """Contact'a bağlı normal faturalarda description genelde boştur, ama
    doluysa da normalize edilip döner — tüketici karar verir."""
    mng = FIXTURE["data"][0]
    assert "description" not in mng["attributes"]  # bu fixture'da yok
    client = AsyncMock()
    client.get.side_effect = [FIXTURE, {"data": []}]

    bills = [b async for b in fetch_purchase_bills(client)]
    assert bills[0].description is None


@pytest.mark.asyncio
async def test_extra_filters_are_merged():
    client = AsyncMock()
    client.get.side_effect = [{"data": []}]

    async for _ in fetch_purchase_bills(
        client, extra_filters={"filter[remaining][gt]": "0"}
    ):
        pass

    _, kwargs = client.get.call_args
    assert kwargs["params"]["filter[remaining][gt]"] == "0"
