from ib_async import *
import asyncio
import logging
import nest_asyncio
import os
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Apply nest_asyncio for Jupyter compatibility
nest_asyncio.apply()

class IBConnection:
    def __init__(self, account_id=None):
        self.ib = IB()
        self.account = account_id
        self.connected = False
        
    async def connect(self, host='127.0.0.1', port=7497, client_id=1):
        """Connect to IB Gateway with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.connected:
                    await self.disconnect()
                    
                logger.info(f"Connecting to IB Gateway at {host}:{port} (attempt {attempt + 1}/{max_retries})")
                await self.ib.connectAsync(host, port, clientId=client_id)
                
                # Get available accounts
                accounts = self.ib.managedAccounts()
                if not accounts:
                    raise ValueError("No accounts available")
                    
                # Set account if not specified
                if not self.account:
                    self.account = accounts[0]
                elif self.account not in accounts:
                    raise ValueError(f"Account {self.account} not found. Available accounts: {accounts}")
                
                self.connected = True
                logger.info(f"Connected to IB Gateway. Using account: {self.account}")
                return True
                
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(2)  # Wait before retrying
                
        raise ConnectionError("Failed to connect after multiple attempts")
    
    async def disconnect(self):
        """Disconnect from IB Gateway"""
        if self.connected:
            await self.ib.disconnectAsync()
            self.connected = False
            logger.info("Disconnected from IB Gateway")
    
    async def get_account_summary(self):
        """Get account summary"""
        if not self.connected:
            raise ConnectionError("Not connected to IB Gateway")
            
        summary = await self.ib.accountSummaryAsync(self.account)
        return {value.tag: float(value.value) for value in summary if value.value.replace('.','').isdigit()}

@asynccontextmanager
async def ib_connection(account_id=None, host='127.0.0.1', port=7497, client_id=1):
    """Async context manager for IB connection"""
    conn = IBConnection(account_id)
    try:
        await conn.connect(host, port, client_id)
        yield conn
    finally:
        await conn.disconnect()
