from types import SimpleNamespace
from typing import cast
from datetime import datetime
from unittest.mock import patch

import backtrader as bt

from .alpaca_broker import AlpacaBroker


class FakeOrder:
    def __init__(self, symbol: str, size: int, buy: bool = True):
        self.size = size if buy else -abs(size)
        self.data = SimpleNamespace(_name=symbol)
        self.exectype = bt.Order.Market
        self._accepted = False
        self._executed_args = None
        self.ref = None

    # broker calls these
    def accept(self):
        self._accepted = True

    def execute(self, **kwargs):
        self._executed_args = kwargs

    def reject(self):
        self._accepted = False


class DummyQuote:
    def __init__(self, bid: float, ask: float):
        self.bid_price = bid
        self.ask_price = ask


class DummyClient:
    def __init__(self, bid: float = 99.0, ask: float = 101.0):
        self._quote = DummyQuote(bid, ask)
        self.validated = False

    def validate_connection(self):
        self.validated = True
        return True

    def get_account_info(self):
        return SimpleNamespace(
            buying_power=100000, id="11111111-1111-1111-1111-111111111111"
        )

    def get_latest_quote(self, symbol: str):
        return self._quote


def test_submit_and_execute_buy_order_updates_cash_and_executes():
    # Patch global client getter
    with patch(
        "backtrader_alpaca.execution.alpaca_broker.get_alpaca_client",
        return_value=DummyClient(99.0, 101.0),
    ):
        broker = AlpacaBroker(paper=True)
        start_cash = broker.get_cash()

        order = FakeOrder(symbol="AAPL", size=10, buy=True)
        # Backtrader types are dynamic; cast to satisfy static checker
        broker.submit(cast(bt.Order, order))

        # executed with ask for buy
        assert order._executed_args is not None
        price = order._executed_args["price"]
        assert price == 101.0

        # cash reduces by size * price
        assert broker.get_cash() == start_cash - (order.size * price)
