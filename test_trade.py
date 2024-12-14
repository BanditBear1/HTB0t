from ib_insync import *
import os
from dotenv import load_dotenv
import random

def place_test_trade():
    load_dotenv()
    
    host = os.getenv('IB_GATEWAY_IP', '127.0.0.1')
    port = int(os.getenv('IB_GATEWAY_PORT', 4002))
    
    ib = IB()
    try:
        # Connect with random client ID
        client_id = random.randint(10000, 99999)
        print(f"Connecting with client ID: {client_id}...")
        ib.connect(host, port, clientId=client_id)
        print(f"Connected: {ib.isConnected()}")
        
        # Create SPY contract
        contract = Stock('SPY', 'SMART', 'USD')
        print("\nPlacing market order for 1 share of SPY...")
        
        # Place market order
        order = MarketOrder('BUY', 1)
        trade = ib.placeOrder(contract, order)
        print(f"Order placed. Initial status: {trade.orderStatus.status}")
        
        # Wait briefly for status update
        ib.sleep(5)
        print(f"Current status: {trade.orderStatus.status}")
        
        if trade.orderStatus.status == 'Filled':
            print(f"Order filled at ${trade.orderStatus.avgFillPrice}")
        else:
            print(f"Order not immediately filled. Please check IB Gateway for final status.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("\nDisconnected from IB Gateway")

if __name__ == "__main__":
    place_test_trade()
