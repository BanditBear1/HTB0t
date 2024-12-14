from ib_insync import *
import os
from dotenv import load_dotenv
import random

def check_connection():
    load_dotenv()
    
    host = os.getenv('IB_GATEWAY_IP', '127.0.0.1')
    port = int(os.getenv('IB_GATEWAY_PORT', 4002))
    
    ib = IB()
    try:
        # Connect to IB with random client ID
        client_id = random.randint(10000, 99999)
        print(f"Attempting to connect with client ID: {client_id}")
        ib.connect(host, port, clientId=client_id)
        print(f"Connected to IB Gateway: {ib.isConnected()}")
        
        if ib.isConnected():
            # Get account info
            account = ib.managedAccounts()
            print(f"Account(s): {account}")
            
            # Get current time from TWS/Gateway
            current_time = ib.reqCurrentTime()
            print(f"IB Gateway Time: {current_time}")
            
            # Keep connection open
            print("\nConnection established and maintained. Press Ctrl+C to exit.")
            while True:
                ib.sleep(1)
                
    except KeyboardInterrupt:
        print("\nReceived disconnect signal")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("Disconnected from IB Gateway")

if __name__ == "__main__":
    check_connection()
