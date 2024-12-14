from src.celery_app import celery_app
from src.services import cache
from src.models import models
from src.models.database import get_celery_db
from sqlalchemy import func
from datetime import datetime, timedelta
import pandas as pd


@celery_app.task
def find_high_low_day(contract_id: int, bar_size: int, bar_type: str, date_str: str):
    date_obj = datetime.strptime(date_str, "%Y%m%d")

    # Assuming 'date' is the day you want to filter on
    start_of_day = datetime.combine(date_obj, datetime.min.time())  # Start of the day
    end_of_day = start_of_day + timedelta(days=1)  # End of the day (exclusive)

    with get_celery_db() as db:
        high = (
            db.query(
                func.max(models.PriceBar.high),
            )
            .filter(
                models.PriceBar.contract_id == contract_id,
                models.PriceBar.bar_size == bar_size,
                models.PriceBar.data_type == bar_type,
                models.PriceBar.date >= start_of_day,
                models.PriceBar.date < end_of_day,  # Exclusive end of the day
            )
            .first()
        )

        low = (
            db.query(
                func.min(models.PriceBar.low),
            )
            .filter(
                models.PriceBar.contract_id == contract_id,
                models.PriceBar.bar_size == bar_size,
                models.PriceBar.data_type == bar_type,
                models.PriceBar.date >= start_of_day,
                models.PriceBar.date < end_of_day,  # Exclusive end of the day
            )
            .first()
        )

        contract = (
            db.query(models.BaseContract)
            .filter(models.BaseContract.id == contract_id)
            .first()
        )

    cached_high = cache.get(f"{contract.symbol}_{bar_type}_high")
    cached_low = cache.get(f"{contract.symbol}_{bar_type}_low")

    if not cached_high or high[0] > cached_high:
        cache.set(f"{contract.symbol}_{bar_type}_high", high[0], 60 * 20)

    if not cached_low or low[0] < cached_low:
        cache.set(f"{contract.symbol}_{bar_type}_low", low[0], 60 * 20)


@celery_app.task
def get_trend(contract_id: str, data_type: str, bar_size: int):
    # TODO: Only calculate from the necessary number of bars

    with get_celery_db() as db:
        bars = (
            db.query(models.PriceBar)
            .filter(
                models.PriceBar.contract_id == contract_id,
                models.PriceBar.data_type == data_type,
                models.PriceBar.bar_size == bar_size,
            )
            .order_by(models.PriceBar.date.asc())
            .all()
        )
        price_bars = pd.DataFrame([bar.__dict__ for bar in bars])

    # Convert the data into a Pandas DataFrame
    data = pd.DataFrame(
        {
            "Date": price_bars["date"],
            "Open": price_bars["open"],
            "High": price_bars["high"],
            "Low": price_bars["low"],
            "Close": price_bars["close"],
            "Volume": price_bars["volume"],
        }
    )

    # Set the 'Date' column as the index
    data.set_index("Date", inplace=True)

    # Calculate RSI with adjusted period for 5-min bars using closing prices
    window_length = 12 * 5
    delta = data["Close"].diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=window_length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window_length).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # Calculate 144 EMA of RSI
    data["RSI_EMA_144"] = data["RSI"].ewm(span=144, adjust=False).mean()

    # Define threshold for RSI EMA
    rsi_ema_threshold = 45

    # Initialize trend column
    data["Trend"] = 0

    # Generate bullish signal when RSI's 144 EMA is above 45
    data.loc[data["RSI_EMA_144"] > rsi_ema_threshold, "Trend"] = 1

    with get_celery_db() as db:
        for index, row in data.iterrows():
            db.query(models.PriceBar).filter(
                models.PriceBar.contract_id == contract_id,
                models.PriceBar.data_type == data_type,
                models.PriceBar.bar_size == bar_size,
                models.PriceBar.date == index,
            ).update({
                "trend": float(row["Trend"]),
                "rsi_ema": float(row["RSI_EMA_144"])
            })

        db.commit()

        contract = (
            db.query(models.BaseContract)
            .filter(models.BaseContract.id == contract_id)
            .first()
        )

    # Cache the latest values
    latest_values = {
        "rsi_ema": float(data["RSI_EMA_144"].iloc[-1]),
        "trend": int(data["Trend"].iloc[-1])
    }

    # Store all values in cache
    for key, value in latest_values.items():
        cache.set(
            f"{contract.symbol}_{data_type}_{key}",
            value,
            60 * 20
        )
