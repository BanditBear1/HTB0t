from ib_async import *
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class OrderManagementService:
    def __init__(self, ib_connection):
        self.ib = ib_connection.ib
        self.account = ib_connection.account
        self.orders = {}  # orderId -> order mapping
        
    async def place_market_order(self, 
                               contract,
                               action: str,
                               quantity: float,
                               transmit: bool = True) -> Dict[str, Any]:
        """Place a market order"""
        order = MarketOrder(
            action=action,
            totalQuantity=quantity,
            transmit=transmit
        )
        
        trade = self.ib.placeOrder(contract, order)
        self.orders[trade.order.orderId] = trade
        
        logger.info(f"Placed {action} market order for {quantity} {contract.symbol}")
        return self._format_trade(trade)
        
    async def place_limit_order(self,
                              contract,
                              action: str,
                              quantity: float,
                              limit_price: float,
                              transmit: bool = True) -> Dict[str, Any]:
        """Place a limit order"""
        order = LimitOrder(
            action=action,
            totalQuantity=quantity,
            lmtPrice=limit_price,
            transmit=transmit
        )
        
        trade = self.ib.placeOrder(contract, order)
        self.orders[trade.order.orderId] = trade
        
        logger.info(f"Placed {action} limit order for {quantity} {contract.symbol} @ {limit_price}")
        return self._format_trade(trade)
        
    async def place_stop_order(self,
                             contract,
                             action: str,
                             quantity: float,
                             stop_price: float,
                             transmit: bool = True) -> Dict[str, Any]:
        """Place a stop order"""
        order = StopOrder(
            action=action,
            totalQuantity=quantity,
            stopPrice=stop_price,
            transmit=transmit
        )
        
        trade = self.ib.placeOrder(contract, order)
        self.orders[trade.order.orderId] = trade
        
        logger.info(f"Placed {action} stop order for {quantity} {contract.symbol} @ {stop_price}")
        return self._format_trade(trade)
        
    async def cancel_order(self, order_id: int) -> bool:
        """Cancel an order by ID"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
            
        trade = self.orders[order_id]
        self.ib.cancelOrder(trade.order)
        logger.info(f"Cancelled order {order_id}")
        return True
        
    async def get_order_status(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get current status of an order"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return None
            
        trade = self.orders[order_id]
        return self._format_trade(trade)
        
    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get all open orders"""
        trades = self.ib.trades()
        return [self._format_trade(t) for t in trades if not t.isDone()]
        
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        positions = await self.ib.reqPositionsAsync()
        return [{
            'symbol': pos.contract.symbol,
            'exchange': pos.contract.exchange,
            'currency': pos.contract.currency,
            'position': pos.position,
            'avg_cost': pos.avgCost
        } for pos in positions]
        
    async def get_portfolio(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        portfolio = await self.ib.accountSummaryAsync(self.account)
        return {
            'net_liquidation': next((v.value for v in portfolio if v.tag == 'NetLiquidation'), None),
            'total_cash_value': next((v.value for v in portfolio if v.tag == 'TotalCashValue'), None),
            'buying_power': next((v.value for v in portfolio if v.tag == 'BuyingPower'), None),
            'gross_position_value': next((v.value for v in portfolio if v.tag == 'GrossPositionValue'), None)
        }
        
    def _format_trade(self, trade) -> Dict[str, Any]:
        """Format trade information"""
        return {
            'order_id': trade.order.orderId,
            'symbol': trade.contract.symbol,
            'action': trade.order.action,
            'order_type': trade.order.orderType,
            'quantity': trade.order.totalQuantity,
            'filled': trade.orderStatus.filled,
            'remaining': trade.orderStatus.remaining,
            'status': trade.orderStatus.status,
            'avg_fill_price': trade.orderStatus.avgFillPrice,
            'last_fill_price': trade.orderStatus.lastFillPrice,
            'why_held': trade.orderStatus.whyHeld
        }
