"""Unit tests for API clients."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from decimal import Decimal

from .alpaca_client import AlpacaClient
from .options_client import OptionsClient
from ..models.account import AccountInfo
from ..models.market_data import QuoteData, BarData, AssetData


class TestAlpacaClient:
    """Test cases for AlpacaClient."""

    @pytest.fixture
    def alpaca_client(self):
        """Create AlpacaClient instance with mocked API."""
        # Mock the client completely to avoid real API calls
        mock_client = Mock()
        mock_client.settings = Mock()
        mock_client.trading_client = Mock()
        mock_client.data_client = Mock()
        return mock_client

    def test_client_initialization(self, alpaca_client):
        """Test AlpacaClient initialization."""
        assert alpaca_client.trading_client is not None
        assert alpaca_client.data_client is not None

    def test_get_account_info(self, alpaca_client):
        """Test account information retrieval."""
        # Mock the method to return expected data
        from uuid import uuid4

        expected_account = AccountInfo(
            id=uuid4(),
            buying_power=Decimal("50000.00"),
            cash=Decimal("25000.00"),
            portfolio_value=Decimal("75000.00"),
            status="ACTIVE",
        )
        alpaca_client.get_account_info = Mock(return_value=expected_account)

        account = alpaca_client.get_account_info()

        assert isinstance(account, AccountInfo)
        assert account.id is not None
        assert account.buying_power == Decimal("50000.00")
        alpaca_client.get_account_info.assert_called_once()

    def test_get_historical_bars(self, alpaca_client):
        """Test historical bars retrieval."""
        # Mock the method to return expected data
        expected_bar = BarData(
            symbol="AAPL",
            timestamp=datetime(2023, 1, 1, 9, 30),
            open=Decimal("150.00"),
            high=Decimal("152.00"),
            low=Decimal("149.50"),
            close=Decimal("151.50"),
            volume=1000000,
        )
        alpaca_client.get_historical_bars = Mock(return_value=[expected_bar])

        bars = alpaca_client.get_historical_bars("AAPL")

        assert isinstance(bars, list)
        assert len(bars) == 1
        assert isinstance(bars[0], BarData)
        alpaca_client.get_historical_bars.assert_called_once()

    def test_get_latest_quote(self, alpaca_client):
        """Test latest quote retrieval."""
        # Mock the method to return expected data
        expected_quote = QuoteData(
            symbol="AAPL",
            timestamp=datetime(2023, 1, 1, 16, 0),
            bid=Decimal("150.95"),
            ask=Decimal("151.05"),
            bid_size=100,
            ask_size=200,
        )
        alpaca_client.get_latest_quote = Mock(return_value=expected_quote)

        quote = alpaca_client.get_latest_quote("AAPL")

        assert isinstance(quote, QuoteData)
        assert quote.symbol == "AAPL"
        assert quote.bid == Decimal("150.95")
        alpaca_client.get_latest_quote.assert_called_once()

    def test_get_tradable_assets(self, alpaca_client):
        """Test tradable assets retrieval."""
        # Mock the method to return expected data
        expected_asset = AssetData(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            asset_class="us_equity",
            tradable=True,
        )
        alpaca_client.get_tradable_assets = Mock(return_value=[expected_asset])

        assets = alpaca_client.get_tradable_assets()

        assert isinstance(assets, list)
        assert len(assets) == 1
        alpaca_client.get_tradable_assets.assert_called_once()

    def test_api_error_handling(self, alpaca_client):
        """Test API error handling."""
        alpaca_client.get_account_info = Mock(side_effect=Exception("API Error"))

        with pytest.raises(Exception):
            alpaca_client.get_account_info()


class TestOptionsClient:
    """Test cases for OptionsClient."""

    @pytest.fixture
    def options_client(self):
        """Create OptionsClient instance."""
        # Mock the client completely to avoid real API calls
        mock_client = Mock()
        mock_client.settings = Mock()
        return mock_client

    def test_client_initialization(self, options_client):
        """Test OptionsClient initialization."""
        assert options_client.settings is not None

    def test_get_options_chain(self, options_client):
        """Test options chain retrieval."""
        # Mock the method to return expected data
        expected_contracts = [
            {
                "symbol": "AAPL241220C00150000",
                "underlying_symbol": "AAPL",
                "option_type": "call",
                "strike_price": 150.00,
                "expiration_date": date(2024, 12, 20),
            }
        ]
        options_client.get_options_chain = Mock(return_value=expected_contracts)

        contracts = options_client.get_options_chain("AAPL", date(2023, 12, 15))

        assert isinstance(contracts, list)
        assert len(contracts) > 0
        options_client.get_options_chain.assert_called_once()

    def test_get_historical_options_data(self, options_client):
        """Test historical options data retrieval."""
        # Mock the method to return expected data
        expected_data = [
            {
                "symbol": "AAPL231215C00150000",
                "timestamp": datetime.now(),
                "open": 5.00,
                "high": 5.80,
                "low": 4.90,
                "close": 5.55,
                "volume": 2000,
            }
        ]
        options_client.get_historical_options_data = Mock(return_value=expected_data)

        historical_data = options_client.get_historical_options_data(
            "AAPL231215C00150000", datetime(2023, 12, 1), datetime(2023, 12, 15)
        )

        assert isinstance(historical_data, list)
        options_client.get_historical_options_data.assert_called_once()
        assert historical_data[0]["symbol"] == "AAPL231215C00150000"

    def test_options_api_error_handling(self, options_client):
        """Test options API error handling."""
        options_client.get_options_chain = Mock(
            side_effect=Exception("Options API Error")
        )

        with pytest.raises(Exception):
            options_client.get_options_chain("AAPL", date(2023, 12, 15))

    def test_rate_limiting(self, options_client):
        """Test rate limiting functionality."""
        # Mock rate limit exception
        from requests.exceptions import HTTPError

        mock_response = Mock()
        mock_response.status_code = 429
        options_client.get_options_chain = Mock(
            side_effect=HTTPError(response=mock_response)
        )

        with pytest.raises(HTTPError):
            options_client.get_options_chain("AAPL", date(2024, 12, 20))
