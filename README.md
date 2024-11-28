# HTB Integrated Trading System

This project integrates the reliable IB connection handling from `ib_async` with HTB's trading infrastructure.

## Setup

1. Create virtual environment:
```bash
python3 -m venv venv
```

2. Activate virtual environment:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install ib_async:
```bash
pip install -e /Users/michaelrobinson/Desktop/ib_async-main
```

## Project Structure

- `src/services/`: Core services
  - `ib_connection.py`: Reliable IB Gateway connection handling using ib_async
  - `market_data.py`: Market data service for stocks, options, and historical data

## Usage

1. Start IB Gateway and log in

2. Use the connection service:
```python
from src.services import ib_connection, MarketDataService

async def main():
    async with ib_connection() as conn:
        # Create market data service
        md = MarketDataService(conn)
        
        # Get stock price
        price = await md.get_stock_price('SPY')
        print(f"SPY price: ${price:,.2f}")
        
        # Get option chain
        options = await md.get_option_chain('SPY')
        print(f"Found {len(options)} options")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

## Features

1. Reliable IB Connection
   - Async connection handling
   - Automatic reconnection
   - Connection pooling
   - Error handling

2. Market Data
   - Real-time stock prices
   - Option chains
   - Historical data
   - Level 2 market data (coming soon)

3. Trading (coming soon)
   - Order management
   - Position tracking
   - Risk management
   - Portfolio analysis
