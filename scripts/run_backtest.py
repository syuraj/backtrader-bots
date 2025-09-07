#!/usr/bin/env python3
import os
import sys
import traceback

# Read flags from environment passed by make
DISPLAY_PLOT = bool(int(os.environ.get('DISPLAY_PLOT', '0')))
VERBOSE = bool(int(os.environ.get('VERBOSE', '0')))

# Force non-interactive backend when display is disabled
if not DISPLAY_PLOT:
    os.environ['MPLBACKEND'] = 'Agg'

# Elevate log level on demand
if VERBOSE:
    os.environ['LOG_LEVEL'] = 'DEBUG'

try:
    sys.path.append('src')
    from backtrader_alpaca.strategies.divergence_strategy import DivergenceStrategy
    from backtrader_alpaca.execution.backtest_runner import run_backtest

    print('[runner] invoking run_backtest ...')
    res = run_backtest(
        DivergenceStrategy,
        symbol=os.environ.get('SYMBOL', 'NQ'),
        days=int(os.environ.get('DAYS', '60')),
        stop_loss_pct=float(os.environ.get('STOP_LOSS_PCT', '0.05')),
        take_profit_pct=float(os.environ.get('TAKE_PROFIT_PCT', '0.10')),
        tsi_fast=int(os.environ.get('TSI_FAST', '25')),
        tsi_slow=int(os.environ.get('TSI_SLOW', '13')),
        ema_period=int(os.environ.get('EMA_PERIOD', '25')),
        entry_limit_offset_pct=float(os.environ.get('ENTRY_LIMIT_OFFSET_PCT', '0.001')),
        display_plot=DISPLAY_PLOT,
        use_market_parent=bool(int(os.environ.get('USE_MARKET_PARENT', '0'))),
        slope_eps=float(os.environ.get('SLOPE_EPS', '1e-6')),
        max_pivot_age_bars=int(os.environ.get('MAX_PIVOT_AGE_BARS', '50')),
        require_both_series=bool(int(os.environ.get('REQUIRE_BOTH_SERIES', '1'))),
        strategy_debug=bool(int(os.environ.get('STRATEGY_DEBUG', '0'))),
    )
    print('[runner] Backtest summary:', res)
except Exception:
    print('[runner] ERROR: backtest failed with exception')
    traceback.print_exc()
    sys.exit(1)
