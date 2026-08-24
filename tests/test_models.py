from karlab_parasut_client.models import normalize_currency


def test_trl_normalizes_to_try():
    assert normalize_currency("TRL") == "TRY"


def test_unknown_currency_passthrough():
    assert normalize_currency("USD") == "USD"


def test_none_defaults_to_try():
    assert normalize_currency(None) == "TRY"
