"""Example strategy using the unified framework."""

from typing import Dict, Any
from decimal import Decimal
import backtrader as bt

from .base_strategy import UnifiedStrategy, StrategyParameters
from ..utils.logger import get_logger

logger = get_logger(__name__)


class UnifiedExampleStrategy(UnifiedStrategy):
    """Example strategy demonstrating unified framework usage."""
    
    params = (
        ('symbol', 'AAPL'),
        ('position_size', 1),
        ('max_position_value', 50000),
        ('stop_loss_pct', 0.05),  # 5% stop loss
        ('take_profit_pct', 0.10),  # 10% take profit
        ('sma_period', 20),  # Simple moving average period
    )
    
    def init_strategy(self):
        """Initialize strategy-specific indicators and state."""
        # Create simple moving average indicator
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.sma_period)
        
        # Strategy state
        self.position_entry_price = None
        self.last_signal = None
        
        logger.info("Unified example strategy initialized",
                   symbol=self.strategy_params.symbol,
                   sma_period=self.params.sma_period,
                   mode=self.trading_mode)
    
    def generate_signals(self) -> Dict[str, Any]:
        """
        Generate trading signals based on simple moving average crossover.
        
        Buy when price crosses above SMA, sell when crosses below.
        """
        # Ensure we have enough data
        if len(self.data) < self.params.sma_period + 1:
            return {'action': 'hold', 'reason': 'Insufficient data for SMA'}
        
        current_price = self.data.close[0]
        previous_price = self.data.close[-1]
        current_sma = self.sma[0]
        previous_sma = self.sma[-1]
        
        current_position = self.getposition(self.data).size
        
        # Generate signals based on SMA crossover
        signal = {'action': 'hold', 'reason': 'No signal'}
        
        # Buy signal: price crosses above SMA and we're not already long
        if (previous_price <= previous_sma and 
            current_price > current_sma and 
            current_position <= 0):
            
            signal = {
                'action': 'buy',
                'size': self.strategy_params.position_size,
                'reason': f'Price {current_price:.2f} crossed above SMA {current_sma:.2f}'
            }
            self.position_entry_price = current_price
        
        # Sell signal: price crosses below SMA and we're long
        elif (previous_price >= previous_sma and 
              current_price < current_sma and 
              current_position > 0):
            
            signal = {
                'action': 'sell',
                'size': current_position,
                'reason': f'Price {current_price:.2f} crossed below SMA {current_sma:.2f}'
            }
        
        # Take profit signal: price up 10% from entry
        elif (current_position > 0 and 
              self.position_entry_price and
              self.strategy_params.take_profit_pct and
              current_price >= self.position_entry_price * (1 + float(self.strategy_params.take_profit_pct))):
            
            signal = {
                'action': 'sell',
                'size': current_position,
                'reason': f'Take profit: {float(self.strategy_params.take_profit_pct):.1%} target reached'
            }
        
        # Log signal if different from last
        if signal['action'] != 'hold' and signal != self.last_signal:
            logger.info("Signal generated",
                       action=signal['action'],
                       reason=signal['reason'],
                       price=current_price,
                       sma=current_sma,
                       position=current_position)
        
        self.last_signal = signal
        return signal
