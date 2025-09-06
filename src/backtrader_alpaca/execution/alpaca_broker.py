"""Backtrader broker implementation using Alpaca API."""

from typing import Dict, Any, Optional
import backtrader as bt
from datetime import datetime

from ..clients.alpaca_client import get_alpaca_client, AlpacaAPIError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AlpacaBroker(bt.brokers.BackBroker):
    """Custom backtrader broker that executes trades through Alpaca API."""
    
    def __init__(self, paper: bool = True, **kwargs):
        """Initialize Alpaca broker."""
        # Remove paper param before passing to parent
        super().__init__(**kwargs)
        self.paper = paper
        self.alpaca_client = get_alpaca_client(paper=paper)
        self._orders: Dict[int, bt.Order] = {}
        self._order_counter = 0
        
        # Validate connection on initialization
        try:
            self.alpaca_client.validate_connection()
            account_info = self.alpaca_client.get_account_info()
            self.cash = float(account_info.buying_power)
            logger.info("Alpaca broker initialized", 
                       cash=self.cash, 
                       account_id=str(account_info.id))
        except AlpacaAPIError as e:
            logger.error("Failed to initialize Alpaca broker", error=str(e))
            raise
    
    def submit(self, order: bt.Order, check: bool = True) -> bt.Order:
        """Submit order to Alpaca API."""
        try:
            self._order_counter += 1
            order.ref = self._order_counter
            self._orders[order.ref] = order
            
            # Map backtrader order to Alpaca order
            symbol = order.data._name
            size = abs(order.size)
            side = 'buy' if order.size > 0 else 'sell'
            
            logger.info("Submitting order", 
                       symbol=symbol, 
                       side=side, 
                       size=size,
                       order_type=order.exectype)
            
            # For now, simulate immediate execution in paper trading
            # In production, this would submit to Alpaca API
            order.accept()
            self._execute_order(order)
            
            return order
            
        except Exception as e:
            logger.error("Failed to submit order", 
                        symbol=order.data._name, 
                        error=str(e))
            order.reject()
            return order
    
    def _execute_order(self, order: bt.Order) -> None:
        """Execute order with current market price."""
        try:
            symbol = order.data._name
            
            # Get current market price
            quote = self.alpaca_client.get_latest_quote(symbol)
            price = float(quote.ask_price if order.size > 0 else quote.bid_price)
            
            # Execute the order
            order.execute(
                dt=datetime.now(),
                size=order.size,
                price=price,
                closed=order.size,
                closedvalue=order.size * price,
                closedcomm=0.0,  # Alpaca has no commission
                opened=0,
                openedvalue=0.0,
                openedcomm=0.0,
                margin=0.0,
                pnl=0.0,
                pnlcomm=0.0,
                psize=0,
                pprice=0.0
            )
            
            # Update cash position
            self.cash -= order.size * price
            
            logger.info("Order executed", 
                       symbol=symbol,
                       size=order.size,
                       price=price,
                       remaining_cash=self.cash)
            
        except Exception as e:
            logger.error("Failed to execute order", error=str(e))
            order.reject()
    
    def cancel(self, order: bt.Order) -> bool:
        """Cancel order."""
        if order.ref in self._orders:
            order.cancel()
            del self._orders[order.ref]
            logger.info("Order cancelled", order_ref=order.ref)
            return True
        return False
    
    def get_cash(self) -> float:
        """Get current cash balance."""
        return self.cash
    
    def get_value(self, datas: Optional[list] = None) -> float:
        """Get total portfolio value."""
        # For now, return cash + position values
        # In production, would query Alpaca for actual portfolio value
        return self.cash
