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
async def test_extra_filters_are_merged():
    client = AsyncMock()
    client.get.side_effect = [{"data": []}]

    async for _ in fetch_purchase_bills(
        client, extra_filters={"filter[remaining][gt]": "0"}
    ):
        pass

    _, kwargs = client.get.call_args
    assert kwargs["params"]["filter[remaining][gt]"] == "0"
