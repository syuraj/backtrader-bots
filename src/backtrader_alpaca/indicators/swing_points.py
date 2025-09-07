"""Custom Backtrader indicator to detect swing highs/lows on any source line.

This uses a centered window of size 2*lookback+1 and confirms a swing point
with a delay of `lookback` bars to keep the logic causal (non-repainting).
"""
from __future__ import annotations

import math
import backtrader as bt


class SwingPoints(bt.Indicator):
    """Detects swing highs and lows on a source line.

    Emits NaN when no swing is confirmed at the current bar.

    Params:
    - lookback (int): k in a centered window of size 2k+1
    - src (LineIterator): optional source line, defaults to `data`
    """

    lines = ("swing_high", "swing_low")
    params = dict(lookback=2, src=None)
    plotinfo = dict(subplot=False)  # draw on price panel
    plotlines = dict(
        swing_high=dict(marker='^', markersize=9.0, color='green', fillstyle='full'),
        swing_low=dict(marker='v', markersize=9.0, color='red', fillstyle='full'),
    )

    def __init__(self) -> None:
        # Do not rely on truthiness of Line objects (raises TypeError). Use None check.
        src = self.p.src if self.p.src is not None else self.data
        self._src = src
        k = int(self.p.lookback)
        p = 2 * k + 1
        # rolling window max/min to compare with centered value later
        self._hh = bt.indicators.Highest(src, period=p)
        self._ll = bt.indicators.Lowest(src, period=p)

    def next(self) -> None:
        k = int(self.p.lookback)
        # not enough history to confirm a centered swing point
        if len(self._src) <= k:
            self.lines.swing_high[0] = math.nan
            self.lines.swing_low[0] = math.nan
            return

        # Confirmed now: compare the center (-k) to the max/min over the last (2k+1) bars ending now
        center_val = float(self._src[-k])
        hh_now = float(self._hh[0])
        ll_now = float(self._ll[0])

        # Use small tolerance for float comparisons
        eps = 1e-10
        is_swing_high = abs(center_val - hh_now) <= eps
        is_swing_low = abs(center_val - ll_now) <= eps

        self.lines.swing_high[0] = float(center_val) if is_swing_high else math.nan
        self.lines.swing_low[0] = float(center_val) if is_swing_low else math.nan
