"""Performance monitoring and reporting system."""

import csv
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date
from pathlib import Path
import math

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pydantic import BaseModel, Field

from ..config.settings import TradingSettings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TradeRecord(BaseModel):
    """Individual trade record."""
    
    timestamp: datetime = Field(..., description="Trade execution timestamp")
    symbol: str = Field(..., description="Trading symbol")
    action: str = Field(..., description="Buy or Sell")
    size: int = Field(..., description="Trade size")
    price: Decimal = Field(..., description="Execution price")
    commission: Decimal = Field(default=Decimal('0'), description="Commission paid")
    pnl: Optional[Decimal] = Field(None, description="Realized P&L")
    strategy: str = Field(..., description="Strategy name")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PositionRecord(BaseModel):
    """Position snapshot record."""
    
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    symbol: str = Field(..., description="Position symbol")
    size: int = Field(..., description="Position size")
    avg_price: Decimal = Field(..., description="Average entry price")
    market_price: Decimal = Field(..., description="Current market price")
    unrealized_pnl: Decimal = Field(..., description="Unrealized P&L")
    market_value: Decimal = Field(..., description="Current market value")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PerformanceMetrics(BaseModel):
    """Performance metrics snapshot."""
    
    timestamp: datetime = Field(..., description="Metrics timestamp")
    portfolio_value: Decimal = Field(..., description="Total portfolio value")
    cash: Decimal = Field(..., description="Available cash")
    equity: Decimal = Field(..., description="Equity value")
    
    # P&L metrics
    total_pnl: Decimal = Field(default=Decimal('0'), description="Total realized P&L")
    unrealized_pnl: Decimal = Field(default=Decimal('0'), description="Total unrealized P&L")
    daily_pnl: Decimal = Field(default=Decimal('0'), description="Daily P&L")
    
    # Performance ratios
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    max_drawdown: Decimal = Field(default=Decimal('0'), description="Maximum drawdown")
    max_drawdown_pct: Decimal = Field(default=Decimal('0'), description="Maximum drawdown percentage")
    
    # Trade statistics
    total_trades: int = Field(default=0, description="Total number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")
    win_rate: Decimal = Field(default=Decimal('0'), description="Win rate percentage")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PerformanceMonitor:
    """Performance monitoring and reporting system."""
    
    def __init__(self, settings: Optional[TradingSettings] = None):
        """Initialize performance monitor."""
        self.settings = settings or TradingSettings()
        
        # Data storage
        self.trades: List[TradeRecord] = []
        self.positions: List[PositionRecord] = []
        self.metrics: List[PerformanceMetrics] = []
        
        # Performance tracking
        self.initial_capital: Optional[Decimal] = None
        self.peak_value: Decimal = Decimal('0')
        self.daily_returns: List[Decimal] = []
        
        # File paths
        self.data_dir = Path(self.settings.data_directory)
        self.trades_file = self.data_dir / "trades.csv"
        self.positions_file = self.data_dir / "positions.csv"
        self.metrics_file = self.data_dir / "performance_metrics.csv"
        
        logger.info("Performance monitor initialized",
                   data_dir=str(self.data_dir))
    
    def record_trade(self, 
                    symbol: str,
                    action: str,
                    size: int,
                    price: float,
                    commission: float = 0.0,
                    pnl: Optional[float] = None,
                    strategy: str = "Unknown") -> TradeRecord:
        """Record a trade execution."""
        trade = TradeRecord(
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            size=size,
            price=Decimal(str(price)),
            commission=Decimal(str(commission)),
            pnl=Decimal(str(pnl)) if pnl is not None else None,
            strategy=strategy
        )
        
        self.trades.append(trade)
        
        logger.info("Trade recorded",
                   symbol=symbol,
                   action=action,
                   size=size,
                   price=price)
        
        return trade
    
    def record_position(self,
                       symbol: str,
                       size: int,
                       avg_price: float,
                       market_price: float) -> PositionRecord:
        """Record a position snapshot."""
        unrealized_pnl = (Decimal(str(market_price)) - Decimal(str(avg_price))) * size
        market_value = Decimal(str(market_price)) * abs(size)
        
        position = PositionRecord(
            timestamp=datetime.now(),
            symbol=symbol,
            size=size,
            avg_price=Decimal(str(avg_price)),
            market_price=Decimal(str(market_price)),
            unrealized_pnl=unrealized_pnl,
            market_value=market_value
        )
        
        self.positions.append(position)
        return position
    
    def update_metrics(self,
                      portfolio_value: float,
                      cash: float,
                      positions: Dict[str, Any]) -> PerformanceMetrics:
        """Update performance metrics."""
        portfolio_decimal = Decimal(str(portfolio_value))
        cash_decimal = Decimal(str(cash))
        equity = portfolio_decimal - cash_decimal
        
        # Initialize capital tracking
        if self.initial_capital is None:
            self.initial_capital = portfolio_decimal
        
        # Update peak value and drawdown
        if portfolio_decimal > self.peak_value:
            self.peak_value = portfolio_decimal
        
        max_drawdown = self.peak_value - portfolio_decimal
        max_drawdown_pct = max_drawdown / self.peak_value if self.peak_value > 0 else Decimal('0')
        
        # Calculate daily return
        if self.metrics:
            last_value = self.metrics[-1].portfolio_value
            daily_return = (portfolio_decimal - last_value) / last_value if last_value > 0 else Decimal('0')
            self.daily_returns.append(daily_return)
        
        # Calculate trade statistics
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in self.trades if t.pnl and t.pnl < 0])
        win_rate = Decimal(str(winning_trades / total_trades)) if total_trades > 0 else Decimal('0')
        
        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # Calculate P&L
        total_pnl = sum([t.pnl for t in self.trades if t.pnl], Decimal('0'))
        unrealized_pnl = sum([pos.unrealized_pnl for pos in self.positions[-len(positions):]], Decimal('0'))
        daily_pnl = portfolio_decimal - (self.metrics[-1].portfolio_value if self.metrics else self.initial_capital)
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            portfolio_value=portfolio_decimal,
            cash=cash_decimal,
            equity=equity,
            total_pnl=total_pnl,
            unrealized_pnl=unrealized_pnl,
            daily_pnl=daily_pnl,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate
        )
        
        self.metrics.append(metrics)
        
        logger.info("Performance metrics updated",
                   portfolio_value=portfolio_value,
                   total_pnl=float(total_pnl),
                   sharpe_ratio=float(sharpe_ratio) if sharpe_ratio else None)
        
        return metrics
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> Optional[Decimal]:
        """Calculate Sharpe ratio from daily returns."""
        if len(self.daily_returns) < 2:
            return None
        
        returns_array = [float(r) for r in self.daily_returns]
        mean_return = sum(returns_array) / len(returns_array)
        
        # Calculate standard deviation
        variance = sum([(r - mean_return) ** 2 for r in returns_array]) / (len(returns_array) - 1)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return None
        
        # Annualize (assuming 252 trading days)
        annual_return = mean_return * 252
        annual_std = std_dev * math.sqrt(252)
        
        sharpe = (annual_return - risk_free_rate) / annual_std
        return Decimal(str(sharpe))
    
    def export_trades_csv(self, filename: Optional[str] = None) -> Path:
        """Export trades to CSV file."""
        if not filename:
            filename = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.data_dir / filename
        
        with open(filepath, 'w', newline='') as csvfile:
            if not self.trades:
                return filepath
            
            fieldnames = list(self.trades[0].dict().keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for trade in self.trades:
                row = trade.dict()
                # Convert Decimal to float for CSV
                for key, value in row.items():
                    if isinstance(value, Decimal):
                        row[key] = float(value)
                writer.writerow(row)
        
        logger.info("Trades exported to CSV", filepath=str(filepath), count=len(self.trades))
        return filepath
    
    def export_metrics_csv(self, filename: Optional[str] = None) -> Path:
        """Export performance metrics to CSV file."""
        if not filename:
            filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.data_dir / filename
        
        with open(filepath, 'w', newline='') as csvfile:
            if not self.metrics:
                return filepath
            
            fieldnames = list(self.metrics[0].dict().keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for metric in self.metrics:
                row = metric.dict()
                # Convert Decimal to float for CSV
                for key, value in row.items():
                    if isinstance(value, Decimal):
                        row[key] = float(value)
                writer.writerow(row)
        
        logger.info("Metrics exported to CSV", filepath=str(filepath), count=len(self.metrics))
        return filepath
    
    def create_equity_curve(self, filename: Optional[str] = None) -> Path:
        """Create equity curve visualization."""
        if not self.metrics:
            raise ValueError("No performance metrics available for plotting")
        
        if not filename:
            filename = f"equity_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = self.data_dir / filename
        
        # Prepare data
        timestamps = [m.timestamp for m in self.metrics]
        portfolio_values = [float(m.portfolio_value) for m in self.metrics]
        
        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(timestamps, portfolio_values, linewidth=2, color='blue', label='Portfolio Value')
        
        # Format plot
        ax.set_title('Portfolio Equity Curve', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Portfolio Value ($)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(timestamps) // 10)))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info("Equity curve created", filepath=str(filepath))
        return filepath
    
    def create_drawdown_chart(self, filename: Optional[str] = None) -> Path:
        """Create drawdown visualization."""
        if not self.metrics:
            raise ValueError("No performance metrics available for plotting")
        
        if not filename:
            filename = f"drawdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = self.data_dir / filename
        
        # Prepare data
        timestamps = [m.timestamp for m in self.metrics]
        drawdowns = [float(m.max_drawdown_pct) * 100 for m in self.metrics]  # Convert to percentage
        
        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.fill_between(timestamps, drawdowns, 0, alpha=0.3, color='red', label='Drawdown')
        ax.plot(timestamps, drawdowns, linewidth=1, color='darkred')
        
        # Format plot
        ax.set_title('Portfolio Drawdown', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Drawdown (%)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Invert y-axis so drawdowns go down
        ax.invert_yaxis()
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(timestamps) // 10)))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info("Drawdown chart created", filepath=str(filepath))
        return filepath
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.metrics:
            return {"error": "No performance data available"}
        
        latest = self.metrics[-1]
        
        return {
            "current_metrics": latest.dict(),
            "total_return": float((latest.portfolio_value - self.initial_capital) / self.initial_capital * 100) if self.initial_capital else 0,
            "total_trades": len(self.trades),
            "data_points": len(self.metrics),
            "tracking_period": {
                "start": self.metrics[0].timestamp.isoformat() if self.metrics else None,
                "end": latest.timestamp.isoformat()
            }
        }
