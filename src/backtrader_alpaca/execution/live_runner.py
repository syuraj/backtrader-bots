"""Live and paper trading execution engine using Backtrader with Alpaca broker."""

import backtrader as bt
from datetime import datetime
from typing import Type, Optional, Dict, Any
import time

from ..utils.logger import get_logger
from ..config.settings import settings
from ..execution.alpaca_broker import AlpacaBroker

logger = get_logger(__name__)


def run_paper_trading(
    strategy_class: Type[bt.Strategy], symbol: str = "AAPL", **strategy_params
) -> None:
    """
    Run paper trading using Backtrader with Alpaca paper broker.

    Args:
        strategy_class: Strategy class to execute
        symbol: Trading symbol
        **strategy_params: Additional strategy parameters
    """
    logger.info(
        "Starting paper trading", symbol=symbol, strategy=strategy_class.__name__
    )

    # Create Cerebro engine
    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(strategy_class, symbol=symbol, **strategy_params)

    # Set Alpaca paper broker
    broker = AlpacaBroker(paper=True)
    cerebro.setbroker(broker)

    # Add live data feed from Alpaca
    from ..clients.alpaca_client import AlpacaClient

    client = AlpacaClient()
    data = client.get_live_data_feed(symbol)
    cerebro.adddata(data)

    # Add analyzers for live monitoring
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    logger.info("Paper trading engine started. Press Ctrl+C to stop.")

    try:
        # Run in live mode (infinite loop)
        cerebro.run(runonce=False, live=True)
    except KeyboardInterrupt:
        logger.info("Paper trading stopped by user")
    except Exception as e:
        logger.error("Paper trading error", error=str(e))
        raise


def run_live_trading(
    strategy_class: Type[bt.Strategy], symbol: str = "AAPL", **strategy_params
) -> None:
    """
    Run live trading using Backtrader with Alpaca live broker.

    Args:
        strategy_class: Strategy class to execute
        symbol: Trading symbol
        **strategy_params: Additional strategy parameters
    """
    logger.warning(
        "Starting LIVE trading", symbol=symbol, strategy=strategy_class.__name__
    )

    # Create Cerebro engine
    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(strategy_class, symbol=symbol, **strategy_params)

    # Set Alpaca live broker
    broker = AlpacaBroker(paper=False)
    cerebro.setbroker(broker)

    # Add live data feed from Alpaca
    from ..clients.alpaca_client import AlpacaClient

    client = AlpacaClient()
    data = client.get_live_data_feed(symbol)
    cerebro.adddata(data)

    # Add analyzers for live monitoring
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    logger.warning("LIVE trading engine started with REAL MONEY. Press Ctrl+C to stop.")

    try:
        # Run in live mode (infinite loop)
        cerebro.run(runonce=False, live=True)
    except KeyboardInterrupt:
        logger.info("Live trading stopped by user")
    except Exception as e:
        logger.error("Live trading error", error=str(e))
        raise


class LiveDataFeed(bt.feeds.DataBase):
    """Custom live data feed for Alpaca streaming data."""

    def __init__(self, symbol: str):
        super().__init__()
        self.symbol = symbol
        self.live = True

    def _load(self):
        """Load next bar from live stream."""
        # In production, this would receive data from Alpaca's WebSocket
        # For now, simulate live data

        if not self.live:
            return False

        # Simulate receiving a new bar every minute
        time.sleep(1)  # Simulate real-time delay

        # Generate random OHLCV bar
        import numpy as np

        base_price = getattr(self, "last_price", 150.0)
        change = np.random.normal(0, 0.5)
        new_price = base_price + change

        # Set OHLCV values
        self.lines.open[0] = base_price
        self.lines.high[0] = max(base_price, new_price) + abs(np.random.normal(0, 0.1))
        self.lines.low[0] = min(base_price, new_price) - abs(np.random.normal(0, 0.1))
        self.lines.close[0] = new_price
        self.lines.volume[0] = np.random.randint(100, 1000)

        # Set datetime
        self.lines.datetime[0] = bt.date2num(datetime.now())

        self.last_price = new_price

        return True

    def stop(self):
        """Stop live data feed."""
        self.live = False
        logger.info("Live data feed stopped", symbol=self.symbol)
