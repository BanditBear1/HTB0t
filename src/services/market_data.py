from ib_async import *
import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self, ib_connection):
        self.ib = ib_connection.ib
        
    async def get_stock_price(self, symbol: str, exchange: str = 'SMART', currency: str = 'USD') -> float:
        """Get current stock price"""
        contract = Stock(symbol, exchange, currency)
        await self.ib.qualifyContractsAsync(contract)
        
        [ticker] = await self.ib.reqTickersAsync(contract)
        price = ticker.marketPrice()
        
        if math.isnan(price):
            price = ticker.last
            if math.isnan(price):
                raise ValueError(f"Unable to get price for {symbol}")
                
        logger.info(f"Current {symbol} Price: ${price:,.2f}")
        return price
        
    async def get_option_chain(self, 
                             underlying_symbol: str,
                             exchange: str = 'SMART',
                             currency: str = 'USD',
                             right: str = None  # 'C' for calls, 'P' for puts, None for both
                             ) -> List[Dict[str, Any]]:
        """Get option chain for a symbol"""
        contract = Stock(underlying_symbol, exchange, currency)
        await self.ib.qualifyContractsAsync(contract)
        
        chains = await self.ib.reqSecDefOptParamsAsync(
            contract.symbol, '', contract.secType, contract.conId
        )
        
        if not chains:
            raise ValueError(f"No option chain found for {underlying_symbol}")
            
        # Get the first chain (usually SMART exchange)
        chain = chains[0]
        
        # Convert to more usable format
        options = []
        for strike in chain.strikes:
            for expiry in chain.expirations:
                if right:
                    rights = [right]
                else:
                    rights = ['C', 'P']
                    
                for r in rights:
                    option = {
                        'symbol': underlying_symbol,
                        'expiry': expiry,
                        'strike': strike,
                        'right': r,
                        'exchange': exchange,
                        'multiplier': chain.multiplier,
                        'currency': currency
                    }
                    options.append(option)
                    
        return options
        
    async def get_option_price(self, option_contract: Option) -> Dict[str, float]:
        """Get current price for an option contract"""
        await self.ib.qualifyContractsAsync(option_contract)
        [ticker] = await self.ib.reqTickersAsync(option_contract)
        
        return {
            'bid': ticker.bid,
            'ask': ticker.ask,
            'last': ticker.last,
            'close': ticker.close,
            'volume': ticker.volume,
            'open_interest': ticker.openInterest
        }
        
    async def get_historical_data(self,
                                contract,
                                duration: str = '1 D',
                                bar_size: str = '1 min',
                                what_to_show: str = 'TRADES',
                                use_rth: bool = True) -> List[Dict[str, Any]]:
        """Get historical data for any contract"""
        bars = await self.ib.reqHistoricalDataAsync(
            contract,
            endDateTime='',
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=1
        )
        
        return [
            {
                'date': bar.date,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'average': bar.average,
                'barCount': bar.barCount
            }
            for bar in bars
        ]
