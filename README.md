# Market Reader and Trading System

This project contains the code to deploy a fully functioning algorithmic trading system with continuous market data monitoring. The system comprises:

- FastAPI app to request market data and read them
- Celery worker to process the query tasks 
- Celery beat to send reading requests
- PostgreSQL database
- Redis database for task processing and caching
- Supervisor for process management and auto-restart

## Project Structure

Key files and their locations:
```
htbot/
├── src/
│   ├── services/
│   │   └── ibapi_service.py     # IB Gateway connection handling
│   ├── tasks/
│   │   ├── market_reader_tasks.py   # Market data collection tasks
│   │   └── celeryconfig.py      # Celery configuration
│   └── models/                  # Database models
├── supervisord.conf             # Supervisor process management config
├── redis.conf                   # Redis configuration
├── .env                        # Environment variables
└── README.md                   # This file
```

## Quick Start

### Starting the Trading System

The system includes a convenient restart script that handles all necessary setup:

```bash
./restart.sh
```

This script will:
1. Stop any existing processes (Redis, Celery, etc.)
2. Clean up stale files and sockets
3. Start supervisor with Redis and Celery worker
4. Start Celery Beat for scheduled tasks
5. Test IB Gateway connection
6. Verify task registration

After running the script, the algo will be ready to trade SPX during market hours (10:00 AM - 3:00 PM ET).

### Monitoring and Maintenance

The system will automatically:
- Monitor SPX price movements every 30 seconds
- Enter trades based on trend and breakout conditions
- Manage positions with predefined risk parameters
- Send email notifications for trade entries and exits

If the system crashes or disconnects:
1. Simply run `./restart.sh` to restore all connections
2. The script will verify everything is working before resuming trading

## Trading Strategy

The system implements an SPX breakout strategy with trend confirmation. Here are the key components:

### Trading Hours
- Entry Window: 10:00 AM - 3:00 PM ET (defined by `entry_time` and `out_time` in market_reader_tasks.py)
- No new positions after 3:00 PM ET
- All positions must be closed by market close

### Data Collection
- Instrument: SPX Index
- Timeframe: 5-minute bars
- Data Type: TRADES
- Updates every 30 seconds (configured in celeryconfig.py)

### Entry Conditions
1. Trend Direction:
   - Calculated using 144-period EMA of RSI
   - Trend = 1 for bullish, -1 for bearish
   - Must have clear trend direction

2. Breakout Rules:
   - Long Entry: Price breaks above daily high when trend = 1
   - Short Entry: Price breaks below daily low when trend = -1
   - Entry prices and contract details sent via email

### Exit Conditions
1. Profit Target:
   - Fixed at $400 profit
   - Tracked via `max_gain` parameter
   - Email notification on profit target hit

2. Stop Loss:
   - Fixed at -$200 loss
   - Email notification on stop loss hit

3. Market Close Exit:
   - All positions closed at 3:00 PM ET (defined by `out_time`)
   - No overnight positions held
   - Email notification with final P&L and trade duration

### Risk Management
- Position Sizing: Fixed risk per trade
- Max Drawdown: Defined in daily_loss_limit
- Trade Duration: Tracked from entry to exit
- Performance Metrics: Stored in PostgreSQL

### Monitoring and Alerts
- Email notifications for:
  - Trade entries with contract details
  - Trade exits with P&L
  - System errors or disconnections
- Real-time P&L tracking
- Daily high/low tracking

The strategy implementation can be found in:
- Entry Logic: `src/tasks/market_reader_tasks.py:stream_spy_trades()`
- Exit Logic: `src/tasks/market_reader_tasks.py:stream_strat_1_pnl()`
- Trade Execution: `src/tasks/order_tasks.py:enter_trade()`

## Process Management

The system uses Supervisor to ensure continuous operation:

- Celery workers are automatically managed and restarted if they crash
- Redis is managed via supervisor for persistence
- All processes are configured to run continuously with proper logging

### Supervisor Configuration

The system uses a supervisor configuration file (`supervisord.conf`) to manage processes:
```ini
[program:celery]
command=venv/bin/celery -A celery_app worker -l info
directory=/Users/michaelrobinson/Desktop/HTBot/htb Current
environment=PYTHONPATH="/Users/michaelrobinson/Desktop/HTBot/htb Current:/Users/michaelrobinson/Desktop/HTBot/htb Current/src"
autostart=true
autorestart=true
```

## Environment Variables

Required environment variables in `.env`:
```bash
IB_GATEWAY_IP=127.0.0.1
IB_GATEWAY_PORT=4002
CELERY_BROKER_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://localhost/htb

# Email Settings (for trade notifications)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
NOTIFICATION_EMAIL=your-email@gmail.com