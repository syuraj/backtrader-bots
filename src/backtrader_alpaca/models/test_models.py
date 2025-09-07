"""Unit tests for data models."""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock

from .account import Account, Position
from .market_data import MarketData, Quote, Trade
from .options import (
    OptionContract, OptionsChain, HistoricalOptionsData, OptionType
)


class TestAccount:
    """Test cases for Account model."""
    
    def test_account_creation(self):
        """Test account object creation with valid data."""
        account = Account(
            id="test_account",
            account_number="123456789",
            status="ACTIVE",
            currency="USD",
            buying_power=Decimal("10000.00"),
            cash=Decimal("5000.00"),
            portfolio_value=Decimal("15000.00"),
            day_trade_count=0,
            pattern_day_trader=False,
            created_at=datetime.now()
        )
        
        assert account.id == "test_account"
        assert account.buying_power == Decimal("10000.00")
        assert account.cash == Decimal("5000.00")
        assert account.portfolio_value == Decimal("15000.00")
        assert not account.pattern_day_trader
    
    def test_account_validation(self):
        """Test account validation rules."""
        with pytest.raises(ValueError):
            Account(
                id="",  # Empty ID should fail
                account_number="123456789",
                status="ACTIVE",
                currency="USD",
                buying_power=Decimal("10000.00"),
                cash=Decimal("5000.00"),
                portfolio_value=Decimal("15000.00"),
                created_at=datetime.now()
            )
    
    def test_position_creation(self):
        """Test position object creation."""
        position = Position(
            symbol="AAPL",
            quantity=Decimal("100"),
            market_value=Decimal("15000.00"),
            cost_basis=Decimal("14000.00"),
            unrealized_pl=Decimal("1000.00"),
            unrealized_plpc=Decimal("0.0714"),
            avg_entry_price=Decimal("140.00"),
            change_today=Decimal("500.00"),
            side="long"
        )
        
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.unrealized_pl == Decimal("1000.00")


class TestMarketData:
    """Test cases for MarketData models."""
    
    def test_market_data_creation(self):
        """Test market data object creation."""
        timestamp = datetime.now()
        market_data = MarketData(
            symbol="AAPL",
            timestamp=timestamp,
            open_price=Decimal("150.00"),
            high_price=Decimal("155.00"),
            low_price=Decimal("149.00"),
            close_price=Decimal("154.00"),
            volume=1000000
        )
        
        assert market_data.symbol == "AAPL"
        assert market_data.timestamp == timestamp
        assert market_data.close_price == Decimal("154.00")
        assert market_data.volume == 1000000
    
    def test_quote_creation(self):
        """Test quote object creation."""
        timestamp = datetime.now()
        quote = Quote(
            symbol="AAPL",
            timestamp=timestamp,
            bid_price=Decimal("153.99"),
            ask_price=Decimal("154.01"),
            bid_size=100,
            ask_size=200
        )
        
        assert quote.symbol == "AAPL"
        assert quote.bid_price == Decimal("153.99")
        assert quote.ask_price == Decimal("154.01")
        assert quote.bid_size == 100
    
    def test_trade_creation(self):
        """Test trade object creation."""
        timestamp = datetime.now()
        trade = Trade(
            symbol="AAPL",
            timestamp=timestamp,
            price=Decimal("154.00"),
            size=500
        )
        
        assert trade.symbol == "AAPL"
        assert trade.price == Decimal("154.00")
        assert trade.size == 500


class TestOptionsModels:
    """Test cases for Options models."""
    
    def test_option_contract_creation(self):
        """Test option contract creation."""
        expiration = date(2024, 12, 20)
        quote_time = datetime.now()
        
        contract = OptionContract(
            symbol="AAPL241220C00150000",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=Decimal("150.00"),
            expiration_date=expiration,
            bid_price=Decimal("5.50"),
            ask_price=Decimal("5.60"),
            last_price=Decimal("5.55"),
            volume=1000,
            open_interest=5000,
            delta=Decimal("0.65"),
            gamma=Decimal("0.02"),
            theta=Decimal("-0.05"),
            vega=Decimal("0.15"),
            rho=Decimal("0.08"),
            implied_volatility=Decimal("0.25"),
            quote_timestamp=quote_time,
            updated_at=quote_time
        )
        
        assert contract.symbol == "AAPL241220C00150000"
        assert contract.underlying_symbol == "AAPL"
        assert contract.option_type == OptionType.CALL
        assert contract.strike_price == Decimal("150.00")
        assert contract.delta == Decimal("0.65")
    
    def test_options_chain_creation(self):
        """Test options chain creation."""
        chain_time = datetime.now()
        expiration = date(2024, 12, 20)
        
        call_contract = OptionContract(
            symbol="AAPL241220C00150000",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=Decimal("150.00"),
            expiration_date=expiration,
            bid_price=Decimal("5.50"),
            ask_price=Decimal("5.60"),
            last_price=Decimal("5.55"),
            volume=1000,
            open_interest=5000,
            delta=Decimal("0.65"),
            gamma=Decimal("0.02"),
            theta=Decimal("-0.05"),
            vega=Decimal("0.15"),
            rho=Decimal("0.08"),
            implied_volatility=Decimal("0.25"),
            quote_timestamp=chain_time,
            updated_at=chain_time
        )
        
        put_contract = OptionContract(
            symbol="AAPL241220P00150000",
            underlying_symbol="AAPL",
            option_type=OptionType.PUT,
            strike_price=Decimal("150.00"),
            expiration_date=expiration,
            bid_price=Decimal("2.50"),
            ask_price=Decimal("2.60"),
            last_price=Decimal("2.55"),
            volume=500,
            open_interest=3000,
            delta=Decimal("-0.35"),
            gamma=Decimal("0.02"),
            theta=Decimal("-0.03"),
            vega=Decimal("0.15"),
            rho=Decimal("-0.05"),
            implied_volatility=Decimal("0.28"),
            quote_timestamp=chain_time,
            updated_at=chain_time
        )
        
        chain = OptionsChain(
            underlying_symbol="AAPL",
            underlying_price=Decimal("154.00"),
            chain_timestamp=chain_time,
            calls=[call_contract],
            puts=[put_contract]
        )
        
        assert chain.underlying_symbol == "AAPL"
        assert chain.underlying_price == Decimal("154.00")
        assert len(chain.calls) == 1
        assert len(chain.puts) == 1
        assert chain.calls[0].option_type == OptionType.CALL
        assert chain.puts[0].option_type == OptionType.PUT
    
    def test_historical_options_data_creation(self):
        """Test historical options data creation."""
        timestamp = datetime.now()
        
        historical_data = HistoricalOptionsData(
            symbol="AAPL241220C00150000",
            timestamp=timestamp,
            open_price=Decimal("5.00"),
            high_price=Decimal("5.80"),
            low_price=Decimal("4.90"),
            close_price=Decimal("5.55"),
            volume=2000,
            delta=Decimal("0.65"),
            gamma=Decimal("0.02"),
            theta=Decimal("-0.05"),
            vega=Decimal("0.15"),
            rho=Decimal("0.08"),
            implied_volatility=Decimal("0.25")
        )
        
        assert historical_data.symbol == "AAPL241220C00150000"
        assert historical_data.close_price == Decimal("5.55")
        assert historical_data.volume == 2000
        assert historical_data.delta == Decimal("0.65")
    
    def test_option_type_enum(self):
        """Test OptionType enum values."""
        assert OptionType.CALL.value == "call"
        assert OptionType.PUT.value == "put"
        
        # Test string conversion
        assert str(OptionType.CALL) == "OptionType.CALL"
        assert str(OptionType.PUT) == "OptionType.PUT"
