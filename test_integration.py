import asyncio
import logging
from src.services.ib_connection import IBConnection
from src.services.market_data import MarketDataService
from src.services.order_management import OrderManagementService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_market_data(market_data: MarketDataService):
    """Test market data functionality"""
    logger.info("Testing market data service...")
    
    # Test stock price
    symbol = "SPY"
    price = await market_data.get_stock_price(symbol)
    logger.info(f"{symbol} price: ${price:,.2f}")
    
    # Test option chain
    options = await market_data.get_option_chain(symbol)
    logger.info(f"Found {len(options)} options for {symbol}")
    
    # Test historical data
    history = await market_data.get_historical_data(symbol, "1 D", "1 min")
    logger.info(f"Got {len(history)} historical bars for {symbol}")

async def test_order_management(order_mgmt: OrderManagementService):
    """Test order management functionality"""
    logger.info("Testing order management service...")
    
    # Get portfolio
    portfolio = await order_mgmt.get_portfolio()
    logger.info(f"Portfolio: {portfolio}")
    
    # Get positions
    positions = await order_mgmt.get_positions()
    logger.info(f"Current positions: {positions}")
    
    # Get open orders
    orders = await order_mgmt.get_open_orders()
    logger.info(f"Open orders: {orders}")

async def main():
    """Main test function"""
    try:
        # Connect to IB
        ib_connection = IBConnection()
        await ib_connection.connect()
        logger.info("Connected to IB Gateway")
        
        # Initialize services
        market_data = MarketDataService(ib_connection)
        order_mgmt = OrderManagementService(ib_connection)
        
        # Run tests
        await test_market_data(market_data)
        await test_order_management(order_mgmt)
        
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise
    finally:
        # Disconnect from IB
        await ib_connection.disconnect()
        logger.info("Disconnected from IB Gateway")

if __name__ == "__main__":
    asyncio.run(main())
