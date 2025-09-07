from types import SimpleNamespace
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock
import pytest

from .alpaca_client import AlpacaClient, AlpacaAPIError


class DummySettings:
    def __init__(self):
        self.alpaca_api_key = "key"
        self.alpaca_secret_key = "secret"
        self.alpaca_base_url = "https://paper-api.alpaca.markets"
        self.environment = "paper"


def make_client():
    return AlpacaClient(settings_obj=DummySettings())


def test_get_latest_quote_missing_symbol_raises_error():
    client = make_client()
    # set private client and configure mock
    client._data_client = Mock()
    client._data_client.get_stock_latest_quote.return_value = {}
    with pytest.raises(AlpacaAPIError):
        client.get_latest_quote("AAPL")


def test_get_historical_bars_rawdata_success():
    client = make_client()
    bar = SimpleNamespace(
        timestamp=datetime(2024, 1, 1, 10, 0, 0),
        open=150.1,
        high=151.2,
        low=149.9,
        close=150.9,
        volume=12345,
    )
    raw = {"AAPL": [bar]}
    client._data_client = Mock()
    client._data_client.get_stock_bars.return_value = raw  # RawData-like
    res = client.get_historical_bars("AAPL", limit=1)
    assert len(res) == 1
    r = res[0]
    assert r.symbol == "AAPL"
    assert float(r.open) == 150.1
    assert float(r.close) == 150.9
    assert r.volume == 12345


def test_get_account_info_happy_path():
    client = make_client()
    fake_acct = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        buying_power=Decimal("10000"),
        cash=Decimal("2500"),
        portfolio_value=Decimal("12500"),
        status="ACTIVE",
    )
    client._trading_client = Mock()
    client._trading_client.get_account.return_value = fake_acct
    acct = client.get_account_info()
    assert float(acct.buying_power) == 10000.0
    assert str(acct.id).startswith("1111")
