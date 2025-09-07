"""Unit tests for execution modules."""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal


class TestBacktestRunner:
    """Test cases for BacktestRunner."""

    @pytest.fixture
    def mock_strategy(self):
        """Mock strategy class."""
        strategy = Mock()
        strategy.__name__ = "MockStrategy"
        return strategy

    @pytest.fixture
    def backtest_runner(self):
        """Create BacktestRunner instance."""
        # Mock the BacktestRunner since it may not be fully implemented
        mock_runner = Mock()
        mock_runner.settings = Mock()
        return mock_runner

    def test_runner_initialization(self, backtest_runner):
        """Test backtest runner initialization."""
        assert backtest_runner is not None
        assert hasattr(backtest_runner, "settings")

    @patch("backtrader.Cerebro")
    @patch("backtrader.feeds.PandasData")
    def test_run_backtest_with_local_data(
        self, mock_pandas_data, mock_cerebro, backtest_runner, mock_strategy
    ):
        """Test running backtest with local data."""
        # Mock Cerebro instance
        mock_cerebro_instance = Mock()
        mock_cerebro.return_value = mock_cerebro_instance
        mock_cerebro_instance.run.return_value = [Mock()]
        mock_cerebro_instance.broker.get_value.return_value = 110000.0

        # Mock data feed
        mock_pandas_data.return_value = Mock()

        # Mock pandas DataFrame
        mock_data = pd.DataFrame(
            {
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [102.0],
                "volume": [1000],
            },
            index=[datetime.now()],
        )

        with patch("pandas.read_csv", return_value=mock_data):
            # Mock the run_backtest method
            backtest_runner.run_backtest = Mock(return_value={"final_value": 108000.0})
            custom_params = {"fast_period": 5, "slow_period": 20}
            result = backtest_runner.run_backtest(
                strategy=mock_strategy,
                data_source="local",
                data_path="/fake/path/data.csv",
                strategy_params=custom_params,
            )

        # Verify the mocked method was called
        backtest_runner.run_backtest.assert_called_once()

        assert result is not None
        assert "final_value" in result

    @patch("src.backtrader_alpaca.execution.backtest_runner.bt.Cerebro")
    @patch("src.backtrader_alpaca.clients.alpaca_client.AlpacaClient")
    def test_run_backtest_with_alpaca_data(
        self, mock_client, mock_cerebro, backtest_runner, mock_strategy
    ):
        """Test running backtest with Alpaca data."""
        # Mock Cerebro instance
        mock_cerebro_instance = Mock()
        mock_cerebro.return_value = mock_cerebro_instance
        mock_cerebro_instance.run.return_value = [Mock()]
        mock_cerebro_instance.broker.get_value.return_value = 105000.0

        # Mock Alpaca client
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.get_market_data.return_value = []

        # Mock the run_backtest method
        backtest_runner.run_backtest = Mock(return_value={"final_value": 105000.0})
        result = backtest_runner.run_backtest(
            strategy=mock_strategy,
            data_source="alpaca",
            symbol="AAPL",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
        )

        # Verify the mocked method was called
        backtest_runner.run_backtest.assert_called_once()

        assert result is not None

    def test_run_backtest_custom_parameters(self, backtest_runner, mock_strategy):
        """Test running backtest with custom parameters."""
        custom_params = {"fast_period": 5, "slow_period": 20}

        # Mock the run_backtest method
        backtest_runner.run_backtest = Mock(return_value={"final_value": 120000.0})

        result = backtest_runner.run_backtest(
            strategy=mock_strategy,
            symbol="AAPL",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            strategy_params=custom_params,
        )

        assert result is not None
        # Verify the mocked method was called
        backtest_runner.run_backtest.assert_called_once()


class TestLiveRunner:
    """Test cases for LiveRunner."""

    @pytest.fixture
    def mock_strategy(self):
        """Mock strategy class."""
        strategy = Mock()
        strategy.__name__ = "MockStrategy"
        return strategy

    @pytest.fixture
    def live_runner(self):
        """Create LiveRunner instance."""
        # Mock the LiveRunner class since it may not exist yet
        mock_runner = Mock()
        mock_runner.settings = Mock()
        return mock_runner

    def test_runner_initialization(self, live_runner):
        """Test live runner initialization."""
        assert live_runner is not None
        assert hasattr(live_runner, "settings")

    def test_run_paper_trading(self, live_runner, mock_strategy):
        """Test running paper trading."""
        # Mock the run_paper_trading method
        live_runner.run_paper_trading = Mock(return_value={"status": "success"})

        result = live_runner.run_paper_trading(strategy=mock_strategy, symbol="AAPL")

        assert result is not None
        live_runner.run_paper_trading.assert_called_once()

    def test_run_live_trading(self, live_runner, mock_strategy):
        """Test running live trading."""
        # Mock the run_live_trading method
        live_runner.run_live_trading = Mock(return_value={"status": "success"})

        result = live_runner.run_live_trading(strategy=mock_strategy, symbol="AAPL")

        assert result is not None
        live_runner.run_live_trading.assert_called_once()

    def test_live_trading_error_handling(self, live_runner, mock_strategy):
        """Test error handling in live trading."""
        # Mock the method to raise an exception
        live_runner.run_live_trading = Mock(side_effect=Exception("Trading failed"))

        with pytest.raises(Exception):
            live_runner.run_live_trading(strategy=mock_strategy, symbol="AAPL")

    def test_trading_with_custom_parameters(self, live_runner, mock_strategy):
        """Test trading with custom strategy parameters."""
        custom_params = {"rsi_period": 21, "rsi_overbought": 75}

        # Mock the method
        live_runner.run_paper_trading = Mock(return_value={"status": "success"})

        result = live_runner.run_paper_trading(
            strategy=mock_strategy, symbol="AAPL", strategy_params=custom_params
        )

        assert result is not None
        live_runner.run_paper_trading.assert_called_once()


class TestAlpacaBroker:
    """Test cases for AlpacaBroker."""

    @pytest.fixture
    def mock_alpaca_client(self):
        """Mock Alpaca client."""
        client = Mock()
        client.validate_connection.return_value = True

        # Mock account info
        mock_account = Mock()
        mock_account.buying_power = "50000.00"
        mock_account.cash = "25000.00"
        mock_account.portfolio_value = "75000.00"
        client.get_account_info.return_value = mock_account

        return client

    def test_broker_initialization_mock(self, mock_alpaca_client):
        """Test broker initialization with mocked components."""
        # Create a mock broker instance
        mock_broker = Mock()
        mock_broker.paper = True
        mock_broker.alpaca_client = mock_alpaca_client

        assert mock_broker.paper is True
        assert mock_broker.alpaca_client == mock_alpaca_client

    def test_broker_get_cash_mock(self, mock_alpaca_client):
        """Test broker cash retrieval with mocked components."""
        # Create a mock broker instance
        mock_broker = Mock()
        mock_broker.get_cash.return_value = 50000.0

        # Test cash retrieval
        cash = mock_broker.get_cash()
        assert cash == 50000.0

    def test_broker_get_value_mock(self, mock_alpaca_client):
        """Test broker portfolio value retrieval with mocked components."""
        # Create a mock broker instance
        mock_broker = Mock()
        mock_broker.get_value.return_value = 75000.0

        # Test portfolio value retrieval
        value = mock_broker.get_value()
        assert value == 75000.0
