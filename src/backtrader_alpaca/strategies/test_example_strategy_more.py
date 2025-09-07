import types
from unittest.mock import Mock, MagicMock

import backtrader as bt

from .example_strategy import ExampleStrategy


class DummyOrder:
    Completed = object()

    def __init__(self, buy: bool, size: int, price: float):
        self.status = DummyOrder.Completed
        self._buy = buy
        self.executed = types.SimpleNamespace(size=size, price=price)

    def isbuy(self) -> bool:
        return self._buy


def test_notify_order_creates_stop_loss():
    # Build a lightweight dummy carrying the attributes notify_order needs
    dummy = types.SimpleNamespace(
        params=types.SimpleNamespace(stop_loss_pct=0.10, symbol="AAPL"),
        sell=Mock(),
    )

    order = DummyOrder(buy=True, size=10, price=100.0)

    # Call ExampleStrategy method as unbound function
    ExampleStrategy.notify_order(dummy, order)

    expected_stop = 100.0 * (1 - float(dummy.params.stop_loss_pct))
    dummy.sell.assert_called_with(size=10, exectype=bt.Order.Stop, price=expected_stop)


def test_take_profit_logic_triggers_sell_when_above_threshold():
    # Create a minimal dummy object with required attrs for next()
    class Dummy:
        def __init__(self):
            self.params = types.SimpleNamespace(
                sma_period=20,
                take_profit_pct=0.10,
                position_size=5,
            )
            self.position_entry_price = 100.0

            # data and sma series mocks; data must support len(self.data)
            class DataMock:
                def __init__(self):
                    self.close = MagicMock()

                def __len__(self):
                    return 999

            self.data = DataMock()
            self.sma = MagicMock()
            self.sell = Mock()
            self.getposition = Mock(return_value=types.SimpleNamespace(size=5))

        def __len__(self):
            # Not used by strategy.next(), but keep for completeness
            return 999

    dummy = Dummy()

    # Values to route execution into take-profit branch
    dummy.data.close.__getitem__.side_effect = lambda idx: 111.0 if idx == 0 else 110.0
    dummy.sma.__getitem__.side_effect = lambda idx: 100.0

    # Call next as unbound method
    ExampleStrategy.next(dummy)

    dummy.sell.assert_called_with(size=5)
