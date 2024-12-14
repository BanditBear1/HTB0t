from src.services.ibapi_service import connect_to_ib
from ib_insync import Index, IB
import time
import signal
import sys
from logging_config import logger

def signal_handler(signum, frame):
    logger.info("Received shutdown signal, cleaning up...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def main():
    ib = IB()
    
    while True:
        try:
            with connect_to_ib() as ib:
                logger.info("IB Connection established")
                
                # Keep connection alive with market data request
                spx = Index('SPX', 'CBOE', 'USD')
                ib.qualifyContracts(spx)
                ticker = ib.reqMktData(spx)
                
                # Run the event loop
                ib.run()
                
        except Exception as e:
            logger.error(f"Error in IB connection: {str(e)}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    main()
