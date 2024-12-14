from redis import Redis
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Redis connection
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_db = int(os.getenv('REDIS_DB', 0))
cache = Redis(host=redis_host, port=redis_port, db=redis_db)

# Get the values
trend = cache.get("SPX_TRADES_trend")
high = cache.get("SPX_TRADES_high")
low = cache.get("SPX_TRADES_low")
rsi_ema = cache.get("SPX_TRADES_rsi_ema")

print("\nCurrent SPX Trading Status:")
print("-" * 25)
print(f"Trend: {int(trend) if trend else 'Not set'} ({('Uptrend' if trend and int(trend) == 1 else 'Downtrend') if trend else 'No trend'})")
print(f"Day High: {float(high) if high else 'Not set'}")
print(f"Day Low: {float(low) if low else 'Not set'}")
print(f"RSI EMA: {float(rsi_ema) if rsi_ema else 'Not set'}")
