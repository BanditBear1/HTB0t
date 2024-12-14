from ib_insync import IB
import os
import time
import random
from contextlib import contextmanager
import logging
from logging_config import logger

@contextmanager
def connect_to_ib(clientId: int = None):
    ib = IB()
    connected = False
    max_retries = 100  
    retry_count = 0
    retry_delay = 5  

    if not clientId:
        clientId = random.randint(1, 32767)

    while not connected and retry_count < max_retries:
        try:
            ib.connect(
                os.getenv("IB_GATEWAY_IP", "127.0.0.1"),
                os.getenv("IB_GATEWAY_PORT", 4002),
                clientId=clientId,
            )
            connected = True
            logger.info(f"Connected to IB Gateway with clientId {clientId}")
            
            ib.reqAccountUpdates(True)  
            ib.commissionReportEvent.clear()
            ib.pendingTickersEvent.clear()
            
        except Exception as e:
            logger.warning(f"Connection attempt {retry_count + 1} failed with clientId {clientId}: {str(e)}")
            clientId = random.randint(1, 32767)  
            retry_count += 1
            time.sleep(retry_delay)

    if not connected:
        raise Exception("Failed to connect after multiple attempts.")

    try:
        yield ib
    finally:
        if connected:
            logger.info(f"Disconnecting clientId {clientId}")
            try:
                ib.disconnect()
            except:
                pass

def handle_disconnect(ib, clientId):
    logger.warning(f"Disconnected from IB Gateway (clientId: {clientId}). Attempting to reconnect...")
    max_reconnect_attempts = 100
    reconnect_delay = 5  
    
    for attempt in range(max_reconnect_attempts):
        try:
            if not ib.isConnected():
                ib.connect(
                    os.getenv("IB_GATEWAY_IP", "127.0.0.1"),
                    os.getenv("IB_GATEWAY_PORT", 4002),
                    clientId=clientId
                )
                logger.info(f"Successfully reconnected to IB Gateway (clientId: {clientId})")
                return
        except Exception as e:
            logger.error(f"Reconnection attempt {attempt + 1} failed: {str(e)}")
            time.sleep(reconnect_delay)
    
    logger.critical(f"Failed to reconnect after {max_reconnect_attempts} attempts")
