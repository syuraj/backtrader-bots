"""Backtest execution engine using Backtrader Cerebro."""

import backtrader as bt
from pathlib import Path
from typing import Type, Optional, Dict, Any

from ..utils.logger import get_logger
from ..config.settings import settings

logger = get_logger(__name__)


def run_backtest(
    strategy_class: Type[bt.Strategy],
    symbol: str = 'AAPL',
    days: int = 60,
    cash: float = 100000.0,
    commission: float = 0.001,
    **strategy_params
) -> Dict[str, Any]:
    """
    Run backtest using Backtrader Cerebro engine.

    Args:
        strategy_class: Strategy class to execute
        symbol: Trading symbol
        days: Number of days of historical data
        cash: Starting cash amount
        commission: Commission rate
        **strategy_params: Additional strategy parameters

    Returns:
        Dict with backtest results
    """
    logger.info("Starting backtest",
                symbol=symbol,
                days=days,
                strategy=strategy_class.__name__)

    # Create Cerebro engine
    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(strategy_class, symbol=symbol, **strategy_params)

    # Add data feed from local CSV files
    from pathlib import Path
    import pandas as pd

    # Look for local data files first
    data_dir = Path("data")
    csv_files = list(data_dir.glob("*.csv"))

    if csv_files:
        # Use first available CSV file
        csv_file = csv_files[0]
        logger.info("Loading data from local file", file=str(csv_file))

        # Extract symbol from filename (e.g., NQ_1min.csv -> NQ)
        actual_symbol = csv_file.stem.split('_')[0]

        # Load CSV data
        df = pd.read_csv(csv_file)

        # Convert date/time columns to datetime index
        if 'date' in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
            df.set_index('datetime', inplace=True)
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)

        # Filter to requested time period if needed
        if len(df) > days * 1440:  # 1440 minutes per day
            df = df.tail(days * 1440)

        # Create Backtrader data feed
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,  # Use index
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1
        )
        cerebro.adddata(data)
    else:
        # Fallback to Alpaca API
        from ..clients.alpaca_client import AlpacaClient
        client = AlpacaClient()
        data = client.get_historical_data(symbol, days)
        cerebro.adddata(data)

    # Set broker parameters
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    # Run backtest
    logger.info("Executing backtest...")
    start_value = cerebro.broker.getvalue()

    results = cerebro.run()
    strategy_result = results[0]

    end_value = cerebro.broker.getvalue()

    # Extract analyzer results
    sharpe = strategy_result.analyzers.sharpe.get_analysis()
    drawdown = strategy_result.analyzers.drawdown.get_analysis()
    trades = strategy_result.analyzers.trades.get_analysis()
    returns = strategy_result.analyzers.returns.get_analysis()

    # Compile results
    display_symbol = actual_symbol if 'actual_symbol' in locals() else symbol
    backtest_results = {
        'symbol': display_symbol,
        'strategy': strategy_class.__name__,
        'start_value': start_value,
        'end_value': end_value,
        'total_return': (end_value - start_value) / start_value * 100,
        'sharpe_ratio': sharpe.get('sharperatio', 0),
        'max_drawdown': abs(drawdown.get('max', {}).get('drawdown', 0)) if drawdown.get('max', {}).get('drawdown', 0) else 0,
        'total_trades': trades.get('total', {}).get('total', 0),
        'winning_trades': trades.get('won', {}).get('total', 0),
        'losing_trades': trades.get('lost', {}).get('total', 0),
        'win_rate': _calculate_win_rate(trades),
        'days': days,
        'commission': commission
    }

    # Log results
    logger.info("Backtest completed",
                total_return=f"{backtest_results['total_return']:.2f}%",
                sharpe_ratio=f"{backtest_results['sharpe_ratio'] or 0:.2f}",
                max_drawdown=f"{backtest_results['max_drawdown'] or 0:.2f}%",
                total_trades=backtest_results['total_trades'])

    # Create timestamped folder for this run
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = Path('backtest_results') / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save results as structured report
    _save_backtest_results(backtest_results, run_dir)

    # Save plot as image file
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt

        # Generate plot and save to file
        figs = cerebro.plot(style='candlestick', barup='green', bardown='red',
                           plotdist=0.5, figsize=(20, 12),
                           fontsize=12, tight=True)

        if figs and len(figs) > 0 and len(figs[0]) > 0:
            fig = figs[0][0]

            # Save the plot to the run directory
            chart_filename = run_dir / 'chart.png'
            fig.savefig(chart_filename, dpi=200, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            plt.close(fig)

            logger.info("Chart saved", file=str(chart_filename))
    except Exception as e:
        logger.warning("Could not generate chart", error=str(e))

    return backtest_results




def _calculate_win_rate(trades: Dict) -> float:
    """Calculate win rate from trade analysis."""
    total_trades = trades.get('total', {}).get('total', 0)
    winning_trades = trades.get('won', {}).get('total', 0)

    if total_trades == 0:
        return 0.0

    return (winning_trades / total_trades) * 100


def _save_backtest_results(results: Dict[str, Any], run_dir: Path) -> None:
    """Save backtest results as structured report in dedicated folder."""
    from datetime import datetime
    import json

    # Create comprehensive backtest report
    report = f"""# Backtest Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Strategy Configuration
- **Symbol**: {results['symbol']}
- **Strategy**: {results['strategy']}
- **Period**: {results['days']} days
- **Commission**: {results['commission']}

## Performance Summary
- **Initial Capital**: ${results['start_value']:,.2f}
- **Final Value**: ${results['end_value']:,.2f}
- **Total Return**: {results['total_return']:.2f}%
- **Sharpe Ratio**: {results['sharpe_ratio']:.4f}
- **Max Drawdown**: {results['max_drawdown']:.2f}%

## Trading Statistics
- **Total Trades**: {results['total_trades']}
- **Winning Trades**: {results['winning_trades']}
- **Losing Trades**: {results['losing_trades']}
- **Win Rate**: {results['win_rate']:.2f}%

## Files Generated
- `report.md` - This summary report
- `results.json` - Raw data in JSON format
- `chart.png` - Performance chart (if generated)
"""

    # Save markdown report
    with open(run_dir / 'report.md', 'w') as f:
        f.write(report)

    # Save raw JSON data
    with open(run_dir / 'results.json', 'w') as f:
        json.dump(results, f, indent=2)

    logger.info("Backtest report saved", folder=str(run_dir))
