"""Example SMA crossover strategy."""

from typing import Any, Optional, cast
import backtrader as bt

from ..utils.logger import get_logger

# from .bt_types import BTData, BTIndicator, BTPosition  # Removed - using Any instead

logger = get_logger(__name__)


class ExampleStrategy(bt.Strategy):
    """Example SMA crossover strategy for equities trading."""

    params = (
        ("symbol", "AAPL"),
        ("position_size", 1),
        ("max_position_value", 50000),
        ("stop_loss_pct", 0.05),  # 5% stop loss
        ("take_profit_pct", 0.10),  # 10% take profit
        ("sma_period", 20),  # Simple moving average period
    )

    # Type hints for Backtrader dynamic attributes
    data: Any
    params: Any  # Backtrader params tuple can't be typed as BTParams
    sma: Any
    position_entry_price: Optional[float]

    def __init__(self) -> None:
        """Initialize strategy."""
        super().__init__()  # type: ignore[misc]

        # Create simple moving average indicator
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.sma_period)  # type: ignore[misc]

        # Strategy state
        self.position_entry_price = None

        logger.info(
            "Example strategy initialized",
            symbol=self.params.symbol,
            sma_period=self.params.sma_period,
        )

    def next(self) -> None:
        """Execute strategy logic on each bar."""
        # Ensure we have enough data
        if len(self.data) < self.params.sma_period + 1:
            return

        current_price = float(self.data.close[0])
        previous_price = float(self.data.close[-1])
        current_sma = float(self.sma[0])
        previous_sma = float(self.sma[-1])

        position = self.getposition(self.data)  # type: ignore[misc]
        current_position = int(position.size) if position.size else 0

        # Buy signal: price crosses above SMA and we're not already long
        if (
            previous_price <= previous_sma
            and current_price > current_sma
            and current_position <= 0
        ):

            self.buy(size=int(self.params.position_size))  # type: ignore[misc]
            self.position_entry_price = current_price
            logger.info("Buy signal", price=current_price, sma=current_sma)

        # Sell signal: price crosses below SMA and we're long
        elif (
            previous_price >= previous_sma
            and current_price < current_sma
            and current_position > 0
        ):

            self.sell(size=int(current_position))
            logger.info("Sell signal", price=current_price, sma=current_sma)

        # Take profit signal: price up 10% from entry
        elif (
            current_position > 0
            and self.position_entry_price
            and self.params.take_profit_pct
            and current_price
            >= self.position_entry_price * (1 + float(self.params.take_profit_pct))
        ):  # type: ignore[misc]

            self.sell(size=int(current_position))
            logger.info(
                "Take profit",
                price=current_price,
                target_pct=self.params.take_profit_pct,
            )

    def notify_order(self, order: Any) -> None:
        """Handle order notifications and create stop-loss orders."""
        if order.status in [order.Completed]:
            action = "Buy" if order.isbuy() else "Sell"
            logger.info(
                f"{action} order completed",
                symbol=self.params.symbol,
                size=order.executed.size,
                price=order.executed.price,
            )

            # Create stop-loss for buy orders
            if order.isbuy() and self.params.stop_loss_pct:
                stop_price = float(order.executed.price * (1 - self.params.stop_loss_pct))  # type: ignore[misc]
                self.sell(
                    size=int(order.executed.size),  # type: ignore[misc]
                    exectype=bt.Order.Stop,
                    price=stop_price,
                )
                logger.info("Stop-loss created", stop_price=stop_price)

    def notify_trade(self, trade: Any) -> None:
        """Handle trade notifications."""
        if trade.isclosed:
            logger.info(
                "Trade closed",
                symbol=self.params.symbol,
                pnl=trade.pnl,
                pnlcomm=trade.pnlcomm,
            )
