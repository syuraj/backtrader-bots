from unittest.mock import patch, Mock

import backtrader as bt

from .live_runner import run_paper_trading, run_live_trading
from ..strategies.example_strategy import ExampleStrategy


def test_run_paper_trading_starts_engine_and_adds_components():
    with (
        patch("backtrader_alpaca.execution.live_runner.bt.Cerebro") as Cerebro,
        patch("backtrader_alpaca.execution.live_runner.AlpacaBroker") as Broker,
        patch("backtrader_alpaca.clients.alpaca_client.AlpacaClient") as Client,
    ):
        cerebro = Mock()
        Cerebro.return_value = cerebro

        client_instance = Mock()
        client_instance.get_live_data_feed.return_value = Mock()
        Client.return_value = client_instance

        broker_instance = Mock()
        Broker.return_value = broker_instance

        # Make run return quickly
        cerebro.run.return_value = []

        run_paper_trading(ExampleStrategy, symbol="AAPL")

        assert Cerebro.called
        assert Broker.called
        assert Client.called
        assert cerebro.addstrategy.called
        assert cerebro.adddata.called
        assert cerebro.addanalyzer.call_count >= 1
        assert cerebro.run.called


def test_run_live_trading_uses_live_broker_and_client():
    with (
        patch("backtrader_alpaca.execution.live_runner.bt.Cerebro") as Cerebro,
        patch("backtrader_alpaca.execution.live_runner.AlpacaBroker") as Broker,
        patch("backtrader_alpaca.clients.alpaca_client.AlpacaClient") as Client,
    ):
        cerebro = Mock()
        Cerebro.return_value = cerebro

        client_instance = Mock()
        client_instance.get_live_data_feed.return_value = Mock()
        Client.return_value = client_instance

        broker_instance = Mock()
        Broker.return_value = broker_instance

        cerebro.run.return_value = []

        run_live_trading(ExampleStrategy, symbol="AAPL")

        Broker.assert_called_with(paper=False)
        assert cerebro.addstrategy.called
        assert cerebro.adddata.called
        assert cerebro.run.called
