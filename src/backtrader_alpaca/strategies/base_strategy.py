"""Unified strategy framework for backtesting, paper, and live trading."""

from abc import abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal
from enum import Enum
import json

import backtrader as bt
from pydantic import BaseModel, Field, validator

from ..config.settings import TradingSettings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TradingMode(str, Enum):
    """Trading execution modes."""
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class StrategyParameters(BaseModel):
    """Base strategy parameter validation."""
    
    # Core parameters
    symbol: str = Field(..., description="Primary trading symbol")
    position_size: int = Field(default=100, gt=0, description="Default position size")
    
    # Risk management
    max_position_value: Optional[Decimal] = Field(None, gt=0, description="Maximum position value in USD")
    stop_loss_pct: Optional[Decimal] = Field(None, gt=0, lt=1, description="Stop loss percentage (0-1)")
    take_profit_pct: Optional[Decimal] = Field(None, gt=0, description="Take profit percentage")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol format."""
        if not v or not v.isalpha():
            raise ValueError("Symbol must be alphabetic characters only")
        return v.upper()
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class UnifiedStrategy(bt.Strategy):
    """
    Abstract base class for unified trading strategies.
    
    Provides mode-agnostic strategy execution across backtest, paper, and live trading
    with automatic environment detection and parameter validation.
    """
    
    # Default parameters - override in subclasses
    params = (
        ('symbol', 'AAPL'),
        ('position_size', 100),
        ('max_position_value', None),
        ('stop_loss_pct', None),
        ('take_profit_pct', None),
    )
    
    def __init__(self):
        """Initialize unified strategy with environment detection."""
        super().__init__()
        
        # Initialize core attributes
        self.settings = TradingSettings()
        self.trading_mode = self._detect_trading_mode()
        self.strategy_params = self._validate_parameters()
        
        # Strategy state
        self.orders: Dict[str, bt.Order] = {}
        self._positions: Dict[str, Any] = {}
        self.risk_metrics: Dict[str, float] = {}
        
        logger.info("Unified strategy initialized",
                   strategy=self.__class__.__name__,
                   mode=self.trading_mode,
                   symbol=self.strategy_params.symbol)
        
        # Call subclass initialization
        self.init_strategy()
    
    def _detect_trading_mode(self) -> TradingMode:
        """Detect current trading mode from environment."""
        if hasattr(self.cerebro, '_runonce'):
            # Backtest mode detection
            return TradingMode.BACKTEST
        elif self.settings.environment == "paper":
            return TradingMode.PAPER
        elif self.settings.environment == "live":
            return TradingMode.LIVE
        else:
            return TradingMode.BACKTEST
    
    def _validate_parameters(self) -> StrategyParameters:
        """Validate and serialize strategy parameters."""
        param_dict = {
            'symbol': self.params.symbol,
            'position_size': self.params.position_size,
            'max_position_value': self.params.max_position_value,
            'stop_loss_pct': self.params.stop_loss_pct,
            'take_profit_pct': self.params.take_profit_pct,
        }
        
        # Remove None values
        param_dict = {k: v for k, v in param_dict.items() if v is not None}
        
        return StrategyParameters(**param_dict)
    
    @abstractmethod
    def init_strategy(self):
        """Initialize strategy-specific logic. Override in subclasses."""
        pass
    
    @abstractmethod
    def generate_signals(self) -> Dict[str, Any]:
        """
        Generate trading signals based on market data.
        
        Returns:
            Dict containing signal information:
            {
                'action': 'buy'|'sell'|'hold',
                'size': int,
                'price': float (optional),
                'reason': str (optional)
            }
        """
        pass
    
    def next(self):
        """Execute strategy logic on each bar."""
        try:
            # Generate signals from strategy logic
            signals = self.generate_signals()
            
            # Process signals with risk management
            self._process_signals(signals)
            
            # Update risk metrics
            self._update_risk_metrics()
            
        except Exception as e:
            logger.error("Strategy execution error",
                        strategy=self.__class__.__name__,
                        error=str(e))
    
    def _process_signals(self, signals: Dict[str, Any]):
        """Process trading signals with risk management."""
        if not signals or signals.get('action') == 'hold':
            return
        
        action = signals.get('action')
        size = signals.get('size', self.strategy_params.position_size)
        price = signals.get('price')
        reason = signals.get('reason', 'Signal generated')
        
        # Apply risk management checks
        if not self._validate_risk_limits(action, size):
            logger.warning("Signal rejected by risk management",
                          action=action,
                          size=size,
                          reason="Risk limits exceeded")
            return
        
        # Execute order
        if action == 'buy':
            order = self.buy(size=size, price=price)
        elif action == 'sell':
            order = self.sell(size=size, price=price)
        else:
            logger.warning("Unknown signal action", action=action)
            return
        
        # Track order
        if order:
            self.orders[f"{action}_{len(self.orders)}"] = order
            logger.info("Order submitted",
                       action=action,
                       size=size,
                       price=price,
                       reason=reason)
    
    def _validate_risk_limits(self, action: str, size: int) -> bool:
        """Validate trade against risk management rules."""
        current_position = self.getposition(self.data).size
        
        # Check maximum position value
        if self.strategy_params.max_position_value:
            current_price = self.data.close[0]
            new_position_value = abs(current_position + (size if action == 'buy' else -size)) * current_price
            
            if new_position_value > float(self.strategy_params.max_position_value):
                return False
        
        # Additional risk checks can be added here
        return True
    
    def _update_risk_metrics(self):
        """Update real-time risk metrics."""
        portfolio_value = self.broker.getvalue()
        cash = self.broker.getcash()
        
        self.risk_metrics.update({
            'portfolio_value': portfolio_value,
            'cash': cash,
            'equity': portfolio_value - cash,
            'leverage': (portfolio_value - cash) / portfolio_value if portfolio_value > 0 else 0
        })
    
    def notify_order(self, order):
        """Handle order notifications with enhanced logging."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            action = "Buy" if order.isbuy() else "Sell"
            logger.info(f"{action} order completed",
                       symbol=self.strategy_params.symbol,
                       size=order.executed.size,
                       price=order.executed.price,
                       mode=self.trading_mode)
            
            # Handle stop-loss and take-profit orders
            if order.isbuy() and self.strategy_params.stop_loss_pct:
                self._create_stop_loss_order(order)
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning("Order failed",
                          symbol=self.strategy_params.symbol,
                          status=order.getstatusname(),
                          mode=self.trading_mode)
        
        # Remove from tracking
        self.orders = {k: v for k, v in self.orders.items() if v != order}
    
    def _create_stop_loss_order(self, parent_order):
        """Create stop-loss order for completed buy order."""
        if not self.strategy_params.stop_loss_pct:
            return
        
        stop_price = parent_order.executed.price * (1 - float(self.strategy_params.stop_loss_pct))
        
        # Create stop-loss order
        stop_order = self.sell(size=parent_order.executed.size,
                              exectype=bt.Order.Stop,
                              price=stop_price)
        
        if stop_order:
            self.orders[f"stop_loss_{len(self.orders)}"] = stop_order
            logger.info("Stop-loss order created",
                       stop_price=stop_price,
                       size=parent_order.executed.size)
    
    def notify_trade(self, trade):
        """Handle trade notifications with performance tracking."""
        if trade.isclosed:
            logger.info("Trade closed",
                       symbol=self.strategy_params.symbol,
                       pnl=trade.pnl,
                       pnlcomm=trade.pnlcomm,
                       mode=self.trading_mode)
    
    def get_strategy_state(self) -> Dict[str, Any]:
        """Get current strategy state for monitoring."""
        return {
            'strategy': self.__class__.__name__,
            'mode': self.trading_mode,
            'parameters': self.strategy_params.dict(),
            'risk_metrics': self.risk_metrics,
            'active_orders': len(self.orders),
            'position': self.getposition(self.data).size if hasattr(self, 'data') else 0
        }
    
    def serialize_parameters(self) -> str:
        """Serialize strategy parameters to JSON."""
        return json.dumps(self.strategy_params.dict(), indent=2)
