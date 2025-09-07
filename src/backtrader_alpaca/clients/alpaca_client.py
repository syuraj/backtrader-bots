"""Alpaca API client for market data and trading operations."""

from typing import List, Optional, Any, Union, cast
from datetime import datetime, timedelta
from decimal import Decimal
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.models import TradeAccount
from alpaca.trading.requests import GetAssetsRequest
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.trading.enums import AssetClass
from alpaca.data.timeframe import TimeFrame
from alpaca.data.models import BarSet, RawData

from ..config.settings import settings
from ..utils.logger import logger
from ..models import AccountInfo, QuoteData, BarData, AssetData

logger = logger


class AlpacaAPIError(Exception):
    """Custom exception for Alpaca API errors."""

    pass


class AlpacaConnectionError(AlpacaAPIError):
    """Exception raised when connection to Alpaca API fails."""

    pass


class AlpacaClient:
    """Alpaca API client with authentication and error handling."""

    def __init__(self, settings_obj=None):
        """Initialize Alpaca client with credentials from settings."""
        self.settings = settings_obj or settings
        self.api_key = self.settings.alpaca_api_key
        self.secret_key = self.settings.alpaca_secret_key
        self.base_url = self.settings.alpaca_base_url

        if not self.api_key or not self.secret_key:
            raise AlpacaConnectionError("Alpaca API credentials not configured")

        # Initialize clients
        self._trading_client: Optional[TradingClient] = None
        self._data_client: Optional[StockHistoricalDataClient] = None
        self.api = None  # For test compatibility

        logger.info(
            "Alpaca client initialized",
            base_url=self.base_url,
            environment=self.settings.environment,
        )

    @property
    def trading_client(self) -> TradingClient:
        """Get or create trading client."""
        if self._trading_client is None:
            self._trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=settings.environment != "live",
            )
        return self._trading_client

    @property
    def data_client(self) -> StockHistoricalDataClient:
        """Get or create data client."""
        if self._data_client is None:
            self._data_client = StockHistoricalDataClient(
                api_key=self.api_key, secret_key=self.secret_key
            )
        return self._data_client

    def validate_connection(self) -> bool:
        """Validate connection to Alpaca API."""
        try:
            account = self.trading_client.get_account()
            account_data: Any = account  # Type hint for Alpaca response
            logger.info(
                "Connection validated successfully",
                account_id=str(account_data.id),
                buying_power=float(account_data.buying_power or 0),
            )
            return True
        except Exception as e:
            logger.error("Connection validation failed", error=str(e))
            raise AlpacaConnectionError(f"Failed to connect to Alpaca API: {e}")

    def get_account_info(self) -> AccountInfo:
        """Get account information."""
        try:
            account_response: Union[TradeAccount, RawData] = (
                self.trading_client.get_account()
            )
            account = cast(TradeAccount, account_response)
            return AccountInfo(
                id=account.id,
                buying_power=Decimal(str(account.buying_power or "0")),
                cash=Decimal(str(account.cash or "0")),
                portfolio_value=Decimal(str(account.portfolio_value or "0")),
                status=str(
                    account.status.value
                    if hasattr(account.status, "value")
                    else account.status
                ),
            )
        except Exception as e:
            logger.error("Failed to get account info", error=str(e))
            raise AlpacaAPIError(f"Failed to get account info: {e}")

    def get_latest_quote(self, symbol: str) -> QuoteData:
        """Get latest quote for a symbol."""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
            quotes = self.data_client.get_stock_latest_quote(request)

            if symbol not in quotes:
                raise AlpacaAPIError(f"No quote data available for {symbol}")

            quote = quotes[symbol]
            return QuoteData(
                symbol=symbol,
                bid=Decimal(str(quote.bid_price)),
                ask=Decimal(str(quote.ask_price)),
                bid_size=int(quote.bid_size),
                ask_size=int(quote.ask_size),
                timestamp=quote.timestamp,
            )
        except Exception as e:
            logger.error("Failed to get latest quote", symbol=symbol, error=str(e))
            raise AlpacaAPIError(f"Failed to get quote for {symbol}: {e}")

    def get_historical_bars(
        self,
        symbol: str,
        timeframe: Optional[TimeFrame] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BarData]:
        """Get historical bar data for a symbol."""
        try:
            if timeframe is None:
                timeframe = TimeFrame.Day  # type: ignore
            if start is None:
                start = datetime.now() - timedelta(days=30)
            if end is None:
                end = datetime.now()

            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=timeframe,  # type: ignore[arg-type]
                start=start,
                end=end,
                limit=limit,
            )

            bars_response: Union[BarSet, RawData] = self.data_client.get_stock_bars(
                request
            )

            # Handle different response types
            if isinstance(bars_response, BarSet):
                # BarSet has symbol as attribute
                if not hasattr(bars_response, symbol):
                    raise AlpacaAPIError(f"No bar data available for {symbol}")
                bar_list = getattr(bars_response, symbol, [])
            else:
                # RawData behaves like a dict
                if symbol not in bars_response:
                    raise AlpacaAPIError(f"No bar data available for {symbol}")
                bar_list = bars_response[symbol]

            result: List[BarData] = []
            for bar in bar_list:
                bar_data: Any = bar  # Type hint for individual bar
                result.append(
                    BarData(
                        symbol=symbol,
                        timestamp=bar_data.timestamp,
                        open=Decimal(str(bar_data.open)),
                        high=Decimal(str(bar_data.high)),
                        low=Decimal(str(bar_data.low)),
                        close=Decimal(str(bar_data.close)),
                        volume=int(bar_data.volume),
                    )
                )

            logger.info(
                "Retrieved historical bars",
                symbol=symbol,
                count=len(result),
                timeframe=str(timeframe),
            )
            return result

        except Exception as e:
            logger.error("Failed to get historical bars", symbol=symbol, error=str(e))
            raise AlpacaAPIError(f"Failed to get bars for {symbol}: {e}")

    def get_tradable_assets(
        self, asset_class: AssetClass = AssetClass.US_EQUITY
    ) -> List[AssetData]:
        """Get list of tradable assets."""
        try:
            request = GetAssetsRequest(asset_class=asset_class)
            assets_response = self.trading_client.get_all_assets(request)
            assets_data: Any = assets_response  # Type hint for Alpaca response

            result: List[AssetData] = []
            for asset in assets_data:
                asset_data: Any = asset  # Type hint for individual asset
                if getattr(asset_data, "tradable", False):
                    result.append(
                        AssetData(
                            symbol=str(getattr(asset_data, "symbol", "")),
                            name=str(getattr(asset_data, "name", "") or ""),
                            exchange=str(
                                getattr(asset_data.exchange, "value", "")
                                if hasattr(asset_data, "exchange")
                                else ""
                            ),
                            asset_class=str(
                                getattr(asset_data.asset_class, "value", "us_equity")
                                if hasattr(asset_data, "asset_class")
                                else "us_equity"
                            ),
                            tradable=bool(getattr(asset_data, "tradable", False)),
                        )
                    )

            logger.info("Retrieved tradable assets", count=len(result))
            return result

        except Exception as e:
            logger.error("Failed to get tradable assets", error=str(e))
            raise AlpacaAPIError(f"Failed to get tradable assets: {e}")

    def get_live_data_feed(self, symbol: str):
        """Create live data feed for Backtrader."""
        import backtrader as bt

        # For now, use historical data as placeholder for live feed
        # In production, this would use Alpaca's streaming WebSocket API
        logger.info("Creating live data feed", symbol=symbol)

        # Get recent historical data to simulate live feed
        start_date = datetime.now() - timedelta(days=5)
        historical_data = self.get_historical_bars(symbol, start=start_date)

        # Convert to Backtrader data feed format
        return bt.feeds.PandasData(dataname=historical_data)

    def get_historical_data(self, symbol: str, days: int):
        """Get historical data for backtesting."""
        import backtrader as bt

        logger.info("Getting historical data for backtest", symbol=symbol, days=days)

        # Get historical bars
        start_date = datetime.now() - timedelta(days=days)
        historical_data = self.get_historical_bars(symbol, start=start_date)

        # Convert to Backtrader data feed format
        return bt.feeds.PandasData(dataname=historical_data)


# Global client instance
_client: Optional[AlpacaClient] = None


def get_alpaca_client(paper: bool = True) -> AlpacaClient:
    """Get or create global Alpaca client instance."""
    global _client
    if _client is None:
        _client = AlpacaClient()
    return _client
