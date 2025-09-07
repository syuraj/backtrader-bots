from types import SimpleNamespace
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
import pandas as pd

import backtrader as bt

from .backtest_runner import run_backtest
from ..strategies.example_strategy import ExampleStrategy


def make_df():
    # minimal df with required columns and datetime index
    df = pd.DataFrame(
        {
            "datetime": pd.date_range(start="2024-01-01", periods=10, freq="T"),
            "open": [1.0] * 10,
            "high": [1.1] * 10,
            "low": [0.9] * 10,
            "close": [1.05] * 10,
            "volume": [100] * 10,
        }
    )
    return df


def test_run_backtest_uses_local_csv_when_available(tmp_path, monkeypatch):
    # create a fake csv file in data/
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_file = data_dir / "AAPL_1min.csv"
    csv_file.write_text("datetime,open,high,low,close,volume\n")

    # patch Path('data') to tmp_path/data
    monkeypatch.chdir(tmp_path)

    # patch pandas.read_csv to return a minimal dataframe
    with patch("pandas.read_csv", return_value=make_df()) as _:
        # Patch bt.Cerebro to avoid heavy run and plotting
        with patch("backtrader_alpaca.execution.backtest_runner.bt.Cerebro") as Cerebro:
            cerebro = Mock()
            cerebro.broker.getvalue.side_effect = [100000.0, 101000.0]
            # analyzers mock outputs
            analyzers = SimpleNamespace(
                sharpe=SimpleNamespace(get_analysis=lambda: {"sharperatio": 1.23}),
                drawdown=SimpleNamespace(
                    get_analysis=lambda: {"max": {"drawdown": 5.0}}
                ),
                trades=SimpleNamespace(
                    get_analysis=lambda: {
                        "total": {"total": 1},
                        "won": {"total": 1},
                        "lost": {"total": 0},
                    }
                ),
                returns=SimpleNamespace(get_analysis=lambda: {}),
            )
            strategy_instance = SimpleNamespace(analyzers=analyzers)
            Cerebro.return_value = cerebro

            cerebro.run.return_value = [strategy_instance]

            # execute
            results = run_backtest(ExampleStrategy, symbol="AAPL", days=1)

            # assertions
            assert results["symbol"] == "AAPL"
            assert results["end_value"] == 101000.0
            assert results["total_trades"] == 1

            # verify data added and strategy added
            assert cerebro.adddata.called
            assert cerebro.addstrategy.called


def test_calculate_win_rate_zero_trades_returns_zero():
    from .backtest_runner import _calculate_win_rate

    trades = {"total": {"total": 0}, "won": {"total": 0}}
    assert _calculate_win_rate(trades) == 0.0
