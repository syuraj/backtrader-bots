"""Divergence between EMA and TSI strategy."""

from typing import Any, Optional, cast
from collections import deque
import math
import backtrader as bt

from ..utils.logger import get_logger
from ..indicators import SwingPoints

logger = get_logger(__name__)

class DivergenceStrategy(bt.Strategy):
    """Divergence between EMA and TSI strategy."""

    params: Any = (
        ("symbol", "AAPL"),
        ("position_size", 1),
        ("max_position_value", 50000),
        ("stop_loss_pct", 0.05),  # 5% stop loss
        ("take_profit_pct", 0.10),  # 10% take profit
        ("sma_period", 20),  # Simple moving average period
        ("tsi_fast", 25),  # TSI fast length (period1)
        ("tsi_slow", 13),  # TSI slow length (period2)
        ("ema_period", 25),  # EMA lookback (example default)
        ("entry_limit_offset_pct", 0.001),  # 0.1% above close for limit parent
        ("use_market_parent", False),  # for testing: market parent in bracket orders
        ("slope_eps", 1e-6),  # divergence slope threshold
        ("max_pivot_age_bars", 50),  # max age of latest pivot pair to be considered
        ("require_both_series", True),  # require both series pivots to be fresh
        ("use_paired_at_price", True),  # evaluate TSI on EMA swing timestamps
        ("paired_max_age_bars", 200),   # max age for paired bars
        ("strategy_debug", False),      # emit detailed debug logs when True
    )

    # Type hints for Backtrader dynamic attributes
    # data: Any
    # sma: Any
    position_entry_price: Optional[float]
    _parent_order: Optional[bt.Order]
    _tp_order: Optional[bt.Order]
    _sl_order: Optional[bt.Order]

    def __init__(self) -> None:
        """Initialize strategy."""
        super().__init__()  # type: ignore[misc]

        # Indicators
        self.tsi = bt.indicators.TSI(
            self.data.close,
            period1=int(self.params.tsi_fast),
            period2=int(self.params.tsi_slow),
        )
        # Set explicit plot names to avoid plotter '__name__' issues
        self.tsi.plotinfo.plotname = "TSI"
        self.tsi.plotinfo.subplot = True
        self.tsi_swings = SwingPoints(src=self.tsi, lookback=1)
        self.tsi_swings.plotinfo.plotname = "TSI Swings"
        self.tsi_swings.plotinfo.plotmaster = self.tsi

        self.ema = bt.indicators.EMA(self.data.close, period=int(self.params.ema_period))
        self.ema.plotinfo.plotmaster = self.data  # draw EMA on price panel
        self.ema.plotinfo.plotname = "EMA"
        self.ema_swings = SwingPoints(src=self.ema, lookback=1)
        self.ema_swings.plotinfo.plotname = "EMA Swings"

        # Strategy state
        self.position_entry_price = None
        self._parent_order = None
        self._tp_order = None
        self._sl_order = None

        # Keep last two confirmed swings for divergence checks: (bar_index, value)
        self._tsi_lows = deque(maxlen=2)
        self._tsi_highs = deque(maxlen=2)
        self._ema_lows = deque(maxlen=2)
        self._ema_highs = deque(maxlen=2)

        logger.info(
            "Divergence strategy initialized",
            symbol=self.params.symbol,
            tsi_fast=self.params.tsi_fast,
            tsi_slow=self.params.tsi_slow,
            ema_period=self.params.ema_period,
        )

    def next(self) -> None:
        """Process each bar."""
        # Current bar index
        bar_idx = len(self.data)

        # Capture confirmed swings for TSI
        tsi_sh = self.tsi_swings.swing_high[0]
        tsi_sl = self.tsi_swings.swing_low[0]
        if not math.isnan(tsi_sl):
            self._tsi_lows.append((bar_idx, float(tsi_sl)))
            if bool(self.params.strategy_debug):
                logger.debug("TSI swing low", bar=bar_idx, value=float(tsi_sl))
        if not math.isnan(tsi_sh):
            self._tsi_highs.append((bar_idx, float(tsi_sh)))
            if bool(self.params.strategy_debug):
                logger.debug("TSI swing high", bar=bar_idx, value=float(tsi_sh))

        # Capture confirmed swings for EMA (plotted on price panel)
        ema_sh = self.ema_swings.swing_high[0]
        ema_sl = self.ema_swings.swing_low[0]
        if not math.isnan(ema_sl):
            self._ema_lows.append((bar_idx, float(ema_sl)))
            if bool(self.params.strategy_debug):
                logger.debug("EMA swing low", bar=bar_idx, value=float(ema_sl))
        if not math.isnan(ema_sh):
            self._ema_highs.append((bar_idx, float(ema_sh)))
            if bool(self.params.strategy_debug):
                logger.debug("EMA swing high", bar=bar_idx, value=float(ema_sh))

        # Compute slopes between most recent two pivots for lows and highs
        def slope(points: deque[tuple[int, float]]) -> Optional[float]:
            if len(points) < 2:
                return None
            (x1, y1), (x2, y2) = points[0], points[1]
            # Enforce freshness of latest pivot (x2)
            max_age = int(self.params.max_pivot_age_bars)
            if (bar_idx - x2) > max_age:
                return None
            dx = (x2 - x1) or 1
            return (y2 - y1) / dx

        def paired_slope_from_indices(line: Any, ix1: int, ix2: int) -> Optional[float]:
            """Compute slope of a Backtrader line between two absolute bar indices.

            Returns None if indices are too far back.
            """
            # Convert absolute index to relative offset from current bar
            off1 = ix1 - bar_idx
            off2 = ix2 - bar_idx
            # Only negative or zero offsets are valid (past/current)
            if off1 > 0 or off2 > 0:
                return None
            try:
                y1 = float(line[off1])
                y2 = float(line[off2])
            except Exception:
                return None
            dx = (ix2 - ix1) or 1
            return (y2 - y1) / dx

        use_paired = bool(self.params.use_paired_at_price)
        if use_paired:
            # Use EMA swing timestamps to compute TSI slopes at the same bars
            low_slope_ema = slope(self._ema_lows)
            high_slope_ema = slope(self._ema_highs)

            def latest_two(points: deque[tuple[int, float]]) -> Optional[tuple[tuple[int, float], tuple[int, float]]]:
                if len(points) < 2:
                    return None
                return points[0], points[1]

            eps_idx_age = int(self.params.paired_max_age_bars)

            low_pair = latest_two(self._ema_lows)
            if low_pair is not None:
                (lx1, _), (lx2, _) = low_pair
                if (bar_idx - lx2) <= eps_idx_age:
                    low_slope_tsi = paired_slope_from_indices(self.tsi, lx1, lx2)
                    if bool(self.params.strategy_debug):
                        logger.debug(
                            "Paired lows",
                            ema_ix1=lx1,
                            ema_ix2=lx2,
                            tsi_slope=low_slope_tsi,
                            ema_slope=low_slope_ema,
                        )
                else:
                    low_slope_tsi = None
            else:
                low_slope_tsi = None

            high_pair = latest_two(self._ema_highs)
            if high_pair is not None:
                (hx1, _), (hx2, _) = high_pair
                if (bar_idx - hx2) <= eps_idx_age:
                    high_slope_tsi = paired_slope_from_indices(self.tsi, hx1, hx2)
                    if bool(self.params.strategy_debug):
                        logger.debug(
                            "Paired highs",
                            ema_ix1=hx1,
                            ema_ix2=hx2,
                            tsi_slope=high_slope_tsi,
                            ema_slope=high_slope_ema,
                        )
                else:
                    high_slope_tsi = None
            else:
                high_slope_tsi = None
        else:
            low_slope_tsi = slope(self._tsi_lows)
            low_slope_ema = slope(self._ema_lows)
            high_slope_tsi = slope(self._tsi_highs)
            high_slope_ema = slope(self._ema_highs)

        # Divergence detection with configurable slope thresholds (avoid near-zero noise)
        eps = float(self.params.slope_eps)
        # Base definitions (require both series on each side)
        bullish_div = (
            low_slope_tsi is not None
            and low_slope_ema is not None
            and low_slope_tsi > eps
            and low_slope_ema < -eps
        )
        bearish_div = (
            high_slope_tsi is not None
            and high_slope_ema is not None
            and high_slope_tsi < -eps
            and high_slope_ema > eps
        )

        # If not requiring both series, accept divergence if either relevant slope condition is met
        if not bool(self.params.require_both_series):
            bullish_div = (
                (low_slope_tsi is not None and low_slope_tsi > eps)
                or (low_slope_ema is not None and low_slope_ema < -eps)
            )
            bearish_div = (
                (high_slope_tsi is not None and high_slope_tsi < -eps)
                or (high_slope_ema is not None and high_slope_ema > eps)
            )

        # Optionally require both series to have fresh pivots; if not, skip signals
        if bool(self.params.require_both_series):
            if low_slope_tsi is None or low_slope_ema is None:
                bullish_div = False
            if high_slope_tsi is None or high_slope_ema is None:
                bearish_div = False

        # Trade rules based on divergence (long/short symmetry)
        size = int(self.params.position_size)
        if bool(self.params.strategy_debug):
            logger.debug(
                "Divergence eval",
                bar=bar_idx,
                use_paired=use_paired,
                eps=float(self.params.slope_eps),
                low_slope_tsi=low_slope_tsi,
                low_slope_ema=low_slope_ema,
                high_slope_tsi=high_slope_tsi,
                high_slope_ema=high_slope_ema,
                bullish_div=bullish_div,
                bearish_div=bearish_div,
            )
        if self.position.size == 0:
            if bullish_div:
                self._submit_bracket("long", size)
                logger.info(
                    "Bullish divergence entry via bracket",
                    bar=bar_idx,
                    low_slope_tsi=low_slope_tsi,
                    low_slope_ema=low_slope_ema,
                )
            elif bearish_div:
                self._submit_bracket("short", size)
                logger.info(
                    "Bearish divergence entry via bracket (short)",
                    bar=bar_idx,
                    high_slope_tsi=high_slope_tsi,
                    high_slope_ema=high_slope_ema,
                )
        elif self.position.size > 0:
            # Manage long position: bearish divergence = exit
            if bearish_div:
                self._cancel_children()
                self.sell(size=size)  # type: ignore[misc]
                logger.info(
                    "Bearish divergence exit (closed long)",
                    bar=bar_idx,
                    high_slope_tsi=high_slope_tsi,
                    high_slope_ema=high_slope_ema,
                )
        elif self.position.size < 0:
            # Manage short position: bullish divergence = exit
            if bullish_div:
                self._cancel_children()
                self.buy(size=size)  # type: ignore[misc]
                logger.info(
                    "Bullish divergence exit (closed short)",
                    bar=bar_idx,
                    low_slope_tsi=low_slope_tsi,
                    low_slope_ema=low_slope_ema,
                )


    def notify_order(self, order: bt.Order) -> None:
        """Handle order notifications."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.position_entry_price = order.executed.price
            else:
                self.position_entry_price = None


    def _submit_bracket(self, side: str, size: int) -> None:
        """Submit a limit parent with OCO TP/SL using buy_bracket/sell_bracket.

        side: 'long' or 'short'
        - long: parent limit above close; TP above; SL below
        - short: parent limit below close; TP below; SL above
        """
        px = float(self.data.close[0])
        off = float(self.params.entry_limit_offset_pct)
        tp_pct = float(self.params.take_profit_pct)
        sl_pct = float(self.params.stop_loss_pct)

        if side == "long":
            entry_px = px * (1.0 + off)
            tp_px = px * (1.0 + tp_pct)
            sl_px = px * (1.0 - sl_pct)
            if bool(self.params.use_market_parent):
                parent, tp_order, sl_order = self.buy_bracket(  # type: ignore[misc]
                    size=size,
                    price=None,
                    limitprice=tp_px,
                    stopprice=sl_px,
                    exectype=bt.Order.Market,
                )
            else:
                parent, tp_order, sl_order = self.buy_bracket(  # type: ignore[misc]
                    size=size,
                    price=entry_px,
                    limitprice=tp_px,
                    stopprice=sl_px,
                    exectype=bt.Order.Limit,
                )
        else:
            entry_px = px * (1.0 + off)
            tp_px = px * (1.0 - tp_pct)
            sl_px = px * (1.0 + sl_pct)
            if bool(self.params.use_market_parent):
                parent, tp_order, sl_order = self.sell_bracket(  # type: ignore[misc]
                    size=size,
                    price=None,
                    limitprice=tp_px,
                    stopprice=sl_px,
                    exectype=bt.Order.Market,
                )
            else:
                parent, tp_order, sl_order = self.sell_bracket(  # type: ignore[misc]
                    size=size,
                    price=entry_px,
                    limitprice=tp_px,
                    stopprice=sl_px,
                    exectype=bt.Order.Limit,
                )

        self._parent_order = parent
        self._tp_order = tp_order
        self._sl_order = sl_order
        logger.info(
            "Submitted bracket",
            side=side,
            parent_price=entry_px,
            tp=tp_px,
            sl=sl_px,
        )

    def _cancel_children(self) -> None:
        if self._tp_order is not None:
            try:
                self.cancel(self._tp_order)
            except Exception:
                pass
            finally:
                self._tp_order = None
        if self._sl_order is not None:
            try:
                self.cancel(self._sl_order)
            except Exception:
                pass
            finally:
                self._sl_order = None