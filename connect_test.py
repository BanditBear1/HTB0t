from src.services.ibapi_service import connect_to_ib
from ib_insync import Index
from dotenv import load_dotenv
load_dotenv()

print("Connecting to IB Gateway...")
with connect_to_ib() as ib:
    # Create SPX contract
    spx = Index('SPX', 'CBOE', 'USD')
    
    # Request market data
    ib.qualifyContracts(spx)
    print("Qualified SPX contract")
    
    ticker = ib.reqMktData(spx)
    ib.sleep(2)  # Give time for data to arrive
    print(f"SPX Last Price: {ticker.last}")
    print("Market data received")
