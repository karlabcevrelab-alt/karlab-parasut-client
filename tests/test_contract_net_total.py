"""Contract testi: Paraşüt'ün alan-anlamı varsayımını kilitler.

Bu test kırılırsa, Paraşüt API'sinin alan semantiği değişmiş demektir —
YOKSA test dosyasını "düzeltip" geçmesini sağlamayın, önce gerçek API
yanıtıyla yeniden doğrulayın. Bkz. karlab reposu
docs/architecture/PARASUT_SYNC_ADR.md, 2026-08-24 net_total/gross_total
hatası ve düzeltmesi.
"""
import json
from decimal import Decimal
from pathlib import Path

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "purchase_bills_page1.json").read_text()
)


def test_net_total_equals_gross_total_plus_vat_minus_discount():
    """net_total (VAT DAHİL) = gross_total (VAT HARİÇ) + total_vat - indirim.

    Bu, 2026-08-24'te KARLAB'ın net_total'ı yanlışlıkla gross_total ile
    değiştirdiği (ve tutarların KDV hariç görünmesine yol açtığı) hatanın
    aynısının bu kütüphanede asla olamayacağını garanti eder.
    """
    for item in FIXTURE["data"]:
        attrs = item["attributes"]
        net_total = Decimal(attrs["net_total"])
        gross_total = Decimal(attrs["gross_total"])
        total_vat = Decimal(attrs["total_vat"])
        discount = Decimal(attrs.get("invoice_discount", "0"))

        assert net_total == gross_total + total_vat - discount, (
            f"purchase_bill {item['id']}: net_total={net_total} != "
            f"gross_total({gross_total}) + total_vat({total_vat}) - "
            f"discount({discount})"
        )


def test_remaining_equals_net_total_when_unpaid():
    """Ödenmemiş (total_paid=0) faturalarda remaining == net_total olmalı —
    karlab-odeme-otomasyonu'nun SupplierBill.amount'unu remaining'den
    türetmesinin güvenli olduğunun kanıtı (ADR Bölüm 6, önkoşul #1)."""
    for item in FIXTURE["data"]:
        attrs = item["attributes"]
        if Decimal(attrs["total_paid"]) == 0:
            assert Decimal(attrs["remaining"]) == Decimal(attrs["net_total"]), (
                f"purchase_bill {item['id']}: ödenmemiş ama remaining != net_total"
            )


def test_net_total_is_the_larger_value_when_vat_present():
    """VAT > 0 olan faturalarda net_total > gross_total olmalı — alan
    isimlerinin İngilizce'deki alışılmış anlamın TERSİ olduğunun kanıtı."""
    for item in FIXTURE["data"]:
        attrs = item["attributes"]
        if Decimal(attrs["total_vat"]) > 0:
            assert Decimal(attrs["net_total"]) > Decimal(attrs["gross_total"])
