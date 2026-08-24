# karlab-parasut-client

KARLAB ve karlab-odeme-otomasyonu'nun ortak Paraşüt `purchase_bills` client'ı.

**Kapsam — SADECE:**
- Paraşüt OAuth2 token alma
- `purchase_bills` çekme (sayfalama, filtreler)
- 429 backoff/retry
- Ham API yanıtını normalize edilmiş, doğrulanmış alanlara çeviren mapping

**Kapsam DIŞI (bilinçli olarak):** DB upsert, IBAN onay/uygunluk mantığı, ödeme
açıklaması kuralları, senkron zamanlaması. Bunlar tüketici uygulamalarda kalır.
Bkz. `karlab` reposundaki `docs/architecture/PARASUT_SYNC_ADR.md` (Bölüm 8).

## Alan anlamları (doğrulanmış — 2026-08-24)

Paraşüt'ün alan adları İngilizce'deki alışılmış "net/gross" anlamının **tersi**:

- `net_total` — **VAT DAHİL** nihai ödenecek tutar (indirimden sonra)
- `gross_total` — **VAT HARİÇ** tutar, `before_taxes_total` ile aynı
- `remaining` — ödenmemiş faturalarda `net_total` ile aynı; kısmi ödemede kalan bakiye

`NormalizedPurchaseBill.net_total` bu yüzden Paraşüt'ün kendi adını birebir korur —
`amount` gibi belirsiz bir isim kullanılmıyor. Bkz. `tests/test_contract_net_total.py`.

## Kullanım

```python
from karlab_parasut_client import ParasutClient, fetch_purchase_bills

client = ParasutClient(
    client_id="...", client_secret="...",
    email="...", password="...",
    company_id="297985",
)

async for bill in fetch_purchase_bills(client, since=date(2026, 5, 1)):
    print(bill.parasut_id, bill.net_total, bill.remaining)
```

## Versiyonlama

Tag'ler (`v0.1.0` vb.) sadece insan-okunur referanstır. Tüketici uygulamalar
`requirements.txt`'te **tam commit SHA'sına** sabitlenir, tag'e değil —
bkz. ADR Bölüm 8.1, sertleştirme #1.
