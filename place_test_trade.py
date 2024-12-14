from ib_insync import *
import os
from dotenv import load_dotenv
import sys
import time

def place_test_trade():
    load_dotenv()
    
    host = os.getenv('IB_GATEWAY_IP', '127.0.0.1')
    port = int(os.getenv('IB_GATEWAY_PORT', 4002))
    
    ib = IB()
    try:
        # Connect to IB
        ib.connect(host, port, clientId=2003)
        print(f"Connected to IB Gateway: {ib.isConnected()}")
        
        # Create SPY ETF contract
        spy = Stock('SPY', 'SMART', 'USD')
        qualified_contracts = ib.qualifyContracts(spy)
        
        if not qualified_contracts:
            print("Error: Could not qualify SPY contract")
            return
            
        contract = qualified_contracts[0]
        print(f"Using contract: {contract}")
        
        # Request market data
        ticker = ib.reqMktData(contract)
        print("Waiting for market data...")
        
        # Wait up to 10 seconds for market data
        for _ in range(10):
            ib.sleep(1)
            if ticker.last:
                break
                
        if not ticker.last:
            print("Error: Could not get market data after 10 seconds")
            return
            
        print(f"\nMarket Data:")
        print(f"Last Price: {ticker.last}")
        print(f"Bid/Ask: {ticker.bid}/{ticker.ask}")
        print(f"Volume: {ticker.volume}")
        
        # Create a market order for 1 share
        order = MarketOrder('BUY', 1)
        order.outsideRth = False  # Only trade during regular trading hours
        
        # Submit the order
        trade = ib.placeOrder(contract, order)
        print(f"\nOrder placed:")
        print(f"Action: {order.action}")
        print(f"Quantity: {order.totalQuantity}")
        print(f"Order Type: Market")
        
        # Monitor order status for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            if trade.orderStatus.status == 'Filled':
                print(f"\nOrder filled!")
                print(f"Fill price: {trade.orderStatus.avgFillPrice}")
                print(f"Filled quantity: {trade.orderStatus.filled}")
                break
            elif trade.orderStatus.status in ['Cancelled', 'Inactive']:
                print(f"\nOrder {trade.orderStatus.status}")
                break
            
            print(f"Current status: {trade.orderStatus.status}")
            ib.sleep(2)
            
        # Cancel order if not filled
        if trade.orderStatus.status not in ['Filled', 'Cancelled', 'Inactive']:
            print("\nCancelling unfilled order...")
            ib.cancelOrder(order)
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("\nDisconnected from IB Gateway")

if __name__ == "__main__":
    place_test_trade()
