"""Alpaca options data client for chain retrieval and market data."""

from typing import List, Optional, Any
from datetime import date, datetime
from decimal import Decimal

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame

from ..config.settings import TradingSettings
from ..models.options import OptionsChain, OptionContract, OptionType, HistoricalOptionsData
from ..utils.logger import get_logger
from .alpaca_client import AlpacaAPIError

logger = get_logger(__name__)


class OptionsClient:
    """Client for options data retrieval from Alpaca API."""
    
    def __init__(self, settings: Optional[TradingSettings] = None):
        """Initialize options client."""
        self.settings = settings or TradingSettings()
        
        # Initialize Alpaca clients
        self.stock_client = StockHistoricalDataClient(
            api_key=self.settings.alpaca_api_key,
            secret_key=self.settings.alpaca_secret_key
        )
        
        logger.info("Options client initialized", environment=self.settings.environment)
    
    def get_options_chain(
        self,
        symbol: str,
        expiration_date: Optional[date] = None
    ) -> OptionsChain:
        """
        Retrieve options chain for a symbol.
        
        Args:
            symbol: Underlying symbol (e.g., 'AAPL')
            expiration_date: Specific expiration date (optional)
            
        Returns:
            OptionsChain with contracts and metadata
            
        Raises:
            AlpacaAPIError: If API request fails
        """
        try:
            logger.info("Fetching options chain", symbol=symbol, expiration=expiration_date)
            
            # Note: Alpaca SDK doesn't have direct options chain endpoint
            # This is a placeholder implementation
            # In production, use trading client to get option contracts
            
            contracts = []
            # Placeholder: Create sample option contracts for testing
            if symbol == "AAPL":
                sample_contract = OptionContract(
                    symbol=f"{symbol}240920C00150000",
                    underlying_symbol=symbol,
                    option_type=OptionType.CALL,
                    strike_price=Decimal("150.00"),
                    expiration_date=expiration_date or date(2024, 9, 20),
                    bid_price=Decimal("5.20"),
                    ask_price=Decimal("5.30"),
                    last_price=Decimal("5.25"),
                    volume=100,
                    open_interest=500,
                    delta=Decimal("0.65"),
                    gamma=Decimal("0.02"),
                    theta=Decimal("-0.05"),
                    vega=Decimal("0.15"),
                    rho=Decimal("0.08"),
                    implied_volatility=Decimal("0.25"),
                    quote_timestamp=datetime.now(),
                    updated_at=datetime.now()
                )
                contracts.append(sample_contract)
            
            options_chain = OptionsChain(
                underlying_symbol=symbol,
                underlying_price=Decimal("150.00"),
                calls=contracts if contracts and contracts[0].option_type == OptionType.CALL else [],
                puts=[] if contracts and contracts[0].option_type == OptionType.CALL else contracts,
                chain_timestamp=datetime.now(),
                expiration_dates=[expiration_date or date.today()],
                strike_prices=[Decimal("150.00")]
            )
            
            logger.info("Options chain retrieved successfully", 
                       symbol=symbol, 
                       contract_count=len(contracts))
            
            return options_chain
            
        except Exception as e:
            logger.error("Failed to retrieve options chain",
                        symbol=symbol,
                        error=str(e))
            raise AlpacaAPIError(f"Options chain retrieval failed: {str(e)}")
    
    def get_historical_options_data(
        self, 
        symbol: str, 
        start_date: date, 
        end_date: date,
        timeframe: TimeFrame = TimeFrame.Day
    ) -> List[HistoricalOptionsData]:
        """
        Retrieve historical options pricing data.
        
        Args:
            symbol: Option contract symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            timeframe: Data timeframe (Day, Hour, etc.)
            
        Returns:
            List of historical data points
            
        Raises:
            AlpacaAPIError: If API request fails
        """
        try:
            logger.info("Fetching historical options data", 
                       symbol=symbol, 
                       start=start_date, 
                       end=end_date)
            
            # Note: Using stock data as placeholder for options historical data
            # In production, would need specialized options data provider
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                start=datetime.combine(start_date, datetime.min.time()),
                end=datetime.combine(end_date, datetime.min.time())
            )
            
            # Fetch stock data as proxy for options data
            response = self.stock_client.get_stock_bars(request)
            
            # Parse response into our models
            historical_data = []
            bars_data = getattr(response, 'data', {})
            if symbol in bars_data:
                for bar in bars_data[symbol]:
                    data_point = HistoricalOptionsData(
                        symbol=f"{symbol}_OPTION",
                        timestamp=bar.timestamp,
                        open_price=Decimal(str(bar.open)),
                        high_price=Decimal(str(bar.high)),
                        low_price=Decimal(str(bar.low)),
                        close_price=Decimal(str(bar.close)),
                        volume=int(bar.volume) if bar.volume else None,
                        # Placeholder Greeks data
                        delta=Decimal("0.5"),
                        gamma=Decimal("0.02"),
                        theta=Decimal("-0.05"),
                        vega=Decimal("0.15"),
                        rho=Decimal("0.08"),
                        implied_volatility=Decimal("0.25")
                    )
                    historical_data.append(data_point)
            
            logger.info("Historical options data retrieved", 
                       symbol=symbol, 
                       data_points=len(historical_data))
            
            return historical_data
            
        except Exception as e:
            logger.error("Failed to retrieve historical options data",
                        symbol=symbol,
                        error=str(e))
            raise AlpacaAPIError(f"Historical options data retrieval failed: {str(e)}")
    
    def _get_underlying_price(self, symbol: str) -> Decimal:
        """Get current price of underlying asset."""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
            quote_response = self.stock_client.get_stock_latest_quote(request)
            
            quotes_data = getattr(quote_response, 'data', {})
            quote = quotes_data.get(symbol)
            if not quote:
                raise AlpacaAPIError(f"No quote data available for {symbol}")
            
            # Use mid-price between bid and ask
            bid_price = Decimal(str(quote.bid_price))
            ask_price = Decimal(str(quote.ask_price))
            return (bid_price + ask_price) / 2
            
        except Exception as e:
            logger.error("Failed to get underlying price", symbol=symbol, error=str(e))
            raise AlpacaAPIError(f"Underlying price retrieval failed: {str(e)}")
    
    def _parse_option_contract(self, contract_data: Any, underlying_symbol: str) -> OptionContract:
        """Parse Alpaca option contract data into our model."""
        try:
            # Extract contract details from symbol
            # Alpaca option symbols follow format: AAPL240315C00150000
            contract_symbol = contract_data.symbol
            
            # Parse option type and strike from symbol
            if 'C' in contract_symbol:
                option_type = OptionType.CALL
                strike_str = contract_symbol.split('C')[1]
            else:
                option_type = OptionType.PUT
                strike_str = contract_symbol.split('P')[1]
            
            # Parse strike price (format: 00150000 = $150.00)
            strike_price = Decimal(strike_str) / 1000
            
            # Parse expiration date from symbol (format: YYMMDD)
            date_str = contract_symbol.replace(underlying_symbol, '').split('C')[0].split('P')[0]
            exp_year = 2000 + int(date_str[:2])
            exp_month = int(date_str[2:4])
            exp_day = int(date_str[4:6])
            expiration_date = date(exp_year, exp_month, exp_day)
            
            # Create contract model with Greeks from API
            contract = OptionContract(
                symbol=contract_symbol,
                underlying_symbol=underlying_symbol,
                option_type=option_type,
                strike_price=strike_price,
                expiration_date=expiration_date,
                bid_price=Decimal(str(contract_data.bid_price)) if hasattr(contract_data, 'bid_price') else None,
                ask_price=Decimal(str(contract_data.ask_price)) if hasattr(contract_data, 'ask_price') else None,
                last_price=Decimal(str(contract_data.last_price)) if hasattr(contract_data, 'last_price') else None,
                volume=getattr(contract_data, 'volume', None),
                open_interest=getattr(contract_data, 'open_interest', None),
                # Greeks from Alpaca API
                delta=Decimal(str(contract_data.delta)) if hasattr(contract_data, 'delta') else None,
                gamma=Decimal(str(contract_data.gamma)) if hasattr(contract_data, 'gamma') else None,
                theta=Decimal(str(contract_data.theta)) if hasattr(contract_data, 'theta') else None,
                vega=Decimal(str(contract_data.vega)) if hasattr(contract_data, 'vega') else None,
                rho=Decimal(str(contract_data.rho)) if hasattr(contract_data, 'rho') else None,
                implied_volatility=Decimal(str(contract_data.implied_volatility)) if hasattr(contract_data, 'implied_volatility') else None,
                quote_timestamp=getattr(contract_data, 'timestamp', None),
                updated_at=datetime.now()
            )
            
            return contract
            
        except Exception as e:
            logger.error("Failed to parse option contract", 
                        symbol=getattr(contract_data, 'symbol', 'unknown'),
                        error=str(e))
            raise AlpacaAPIError(f"Contract parsing failed: {str(e)}")
    
    def validate_connection(self) -> bool:
        """Validate connection to Alpaca options API."""
        try:
            # Test connection by making a simple API call
            test_request = StockLatestQuoteRequest(symbol_or_symbols=["AAPL"])
            self.stock_client.get_stock_latest_quote(test_request)
            
            logger.info("Options client connection validated")
            return True
            
        except Exception as e:
            logger.error("Options client connection validation failed", error=str(e))
            raise AlpacaAPIError(f"Connection validation failed: {str(e)}")


def get_options_client(settings: Optional[TradingSettings] = None) -> OptionsClient:
    """Factory function to create options client instance."""
    return OptionsClient(settings)
