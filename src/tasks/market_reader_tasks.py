from src.celery_app import celery_app
from src.logging_config import logger
import os
from fastapi import Depends
from sqlalchemy.orm import Session
from src.models.database import get_celery_db
from src.services import (
    prices_service,
    contracts_service,
    ibapi_service,
    calendar_service,
    cache,
    notification_service,
)
from src.services.ibapi_service import ib_index
import asyncio
import json
from src.models.models import Stock, PriceBar, Future, Option, Forex, Index
from src.models import schemas
import psutil
from datetime import datetime, timedelta
from ib_insync import (
    Stock as ib_stock,
    Option as ib_option,
    ContFuture as ib_future,
    Forex as ib_forex,
    Index as ib_index,
    RealTimeBarList,
    BarData,
)
from pytz import timezone
from src.tasks import trend_tasks, order_tasks, stocks_tasks


entry_time = datetime.strptime("10:00:00", "%H:%M:%S").time()
out_time = datetime.strptime("15:00:00", "%H:%M:%S").time()
momentum_threshold = 3


@celery_app.task
def check_streams():
    # To check entries
    stream_spx_trades.delay()

    # To check strat 1
    stream_strat_1_pnl.delay()

    # We check strat 2
    stream_strat_2.delay()


@celery_app.task
def stream_spx_trades():
    # First we get the past data
    with get_celery_db() as db:
        index = contracts_service.get_contract_by_symbol(db, "SPX", "Index")

        with ibapi_service.connect_to_ib() as ib:
            bars, open_bar = prices_service.get_add_price_bars(
                ib,
                ib_index("SPX", "SMART"),
                "TRADES",
                index.id,
                "Index",
                5,
                [],
                db,
                True,
            )

        if bars:
            db.add_all(bars)
            db.commit()

            last_bar = (
                db.query(PriceBar)
                .filter(
                    PriceBar.contract_id == index.id,
                    PriceBar.bar_size == 5,
                    PriceBar.data_type == "TRADES",
                )
                .order_by(PriceBar.timestamp.desc())
                .first()
            )

            cache.set(
                f"SPX_TRADE_5C",
                schemas.PriceBar(
                    id=last_bar.id,
                    date=last_bar.date,
                    open=last_bar.open,
                    high=last_bar.high,
                    low=last_bar.low,
                    close=last_bar.close,
                    volume=last_bar.volume,
                ).model_dump_json(),
                60 * 20,
            )
            trend_tasks.find_high_low_day.delay(
                index.id, 5, "TRADES", datetime.now().strftime("%Y%m%d")
            )
            trend_tasks.get_trend.delay(index.id, "TRADES", 5)

        else:
            last_bar = (
                db.query(PriceBar)
                .filter(
                    PriceBar.contract_id == index.id,
                    PriceBar.bar_size == 5,
                    PriceBar.data_type == "TRADES",
                )
                .order_by(PriceBar.timestamp.desc())
                .first()
            )

    open_bar: BarData = open_bar

    cache.set(
        f"SPX_TRADE_5O",
        schemas.PriceBar(
            id=0,
            date=open_bar.date,
            open=open_bar.open,
            high=open_bar.high,
            low=open_bar.low,
            close=open_bar.close,
            volume=open_bar.volume,
        ).model_dump_json(),
        60 * 20,
    )

    logger.warning(f"SPX last price: {open_bar.close}")
    now = datetime.now(timezone("America/New_York")).time()

    # Now we check to enter:
    trend = cache.get("SPX_TRADES_trend")
    high = cache.get("SPX_TRADES_high")
    low = cache.get("SPX_TRADES_low")

    if not trend or not high or not low:
        trend_tasks.find_high_low_day(
            index.id, 5, "TRADES", datetime.now().strftime("%Y%m%d")
        )
        trend_tasks.get_trend(index.id, "TRADES", 5)

        trend = cache.get("SPX_TRADES_trend")
        high = cache.get("SPX_TRADES_high")
        low = cache.get("SPX_TRADES_low")

    logger.warning(f"Trend: {trend}, High: {high}, Low: {low}")

    if now < entry_time or now > out_time:
        return

    trade_info = cache.get("trade")

    if trade_info:
        # We have already entered the structure
        # If we are right, another function will deal with it
        # If we are wrong, we keep the currently sold contract
        return

    if (trend == 1 and open_bar.high > high) or (trend == -1 and open_bar.low < low):
        logger.warning("Entering SPX")
        order_tasks.enter_trade.delay(trend)


@celery_app.task
def stream_strat_1_pnl():
    trade_info = cache.get("trade")
    if not trade_info:
        return

    direction, max_gain = map(float, trade_info.split(":"))
    trade_start_time = cache.get("trade_start_time")
    if not trade_start_time:
        trade_start_time = datetime.now(timezone("America/New_York"))
        cache.set("trade_start_time", trade_start_time.isoformat())
    else:
        trade_start_time = datetime.fromisoformat(trade_start_time)

    trades = ["buy", "sell"]
    now = datetime.now(timezone("America/New_York")).time()

    cur_pnl = 0

    still_have_buy = False
    buy_price = 0
    sell_price = 0

    for trade_type in trades:
        order_info = cache.get(f"s1_{trade_type}")

        if not order_info:
            continue

        contract_id, avg_price = map(float, order_info.split(":"))

        with get_celery_db() as db:
            contract = (
                db.query(models.Option)
                .filter(models.Option.id == int(contract_id))
                .first()
            )

            with ibapi_service.connect_to_ib() as ib:
                cur_price = prices_service.get_last_price(ib, contract)

                if trade_type == "buy":
                    still_have_buy = True
                    buy_price = avg_price
                    cur_pnl -= (cur_price - avg_price) * 100
                else:
                    sell_price = avg_price
                    cur_pnl += (avg_price - cur_price) * 100

    if cur_pnl > max_gain:
        cache.set("trade", f"{direction}:{cur_pnl}")

    logger.warning(f"Current PnL: {cur_pnl}")

    # Exit conditions
    should_exit = False
    exit_reason = ""

    if now >= out_time:
        should_exit = True
        exit_reason = "Time-based exit"
    elif cur_pnl <= -200:
        should_exit = True
        exit_reason = "Stop loss hit"
    elif cur_pnl >= 400:
        should_exit = True
        exit_reason = "Profit target reached"

    if should_exit:
        # Calculate trade duration
        duration = datetime.now(timezone("America/New_York")) - trade_start_time
        duration_str = str(duration).split('.')[0]  # Remove microseconds

        # Send exit notification
        message = notification_service.format_trade_exit_message(cur_pnl, duration_str)
        notification_service.send_email_notification(f"Trade Exit - {exit_reason}", message)

        order_tasks.exit_trade.delay()
        cache.delete("trade")
        cache.delete("trade_start_time")


@celery_app.task
def stream_strat_2():
    trade_data = [("call", 1), ("put", -1)]
    now = datetime.now(timezone("America/New_York")).time()
    entry_time = datetime.strptime("09:30:00", "%H:%M:%S").time()

    for trade_type, direction in trade_data:
        trade_info = cache.get(f"s2_{trade_type}")

        if not trade_info:
            if entry_time < now < out_time:
                logger.warning(f"Entering STRAT 2 {trade_type.upper()}")

                order_tasks.enter_strat_2(direction)

            continue

        order_id, option_id, price = map(float, trade_info.split(":"))

        with get_celery_db() as db:
            option = db.query(Option).filter(Option.id == int(option_id)).first()
            contract = contracts_service.db_to_ib_option_contracts([option])[0].option

            with ibapi_service.connect_to_ib() as ib:
                ib_contract = ib.qualifyContracts(contract)[0]
                bars, open_bar = prices_service.get_add_price_bars(
                    ib, ib_contract, "BID", option.id, "Option", 15, [], db, True
                )

            if bars:
                db.add_all(bars)
                db.commit()
                last_closed_bar = bars[-1]

            else:
                last_closed_bar = (
                    db.query(PriceBar)
                    .filter(
                        PriceBar.contract_id == option_id,
                        PriceBar.bar_size == 15,
                        PriceBar.data_type == "BID",
                    )
                    .order_by(PriceBar.date.desc())
                    .first()
                )

            last_closed_bar = schemas.PriceBar(
                id=last_closed_bar.id,
                date=last_closed_bar.date,
                open=last_closed_bar.open,
                high=last_closed_bar.high,
                low=last_closed_bar.low,
                close=last_closed_bar.close,
                volume=last_closed_bar.volume,
            )

        if open_bar:
            cache.set(
                f"STRAT_2_{trade_type.upper()}_15O",
                schemas.PriceBar(**open_bar.__dict__).model_dump_json(),
                60 * 5,
            )
            logger.warning(f"CURRENT {trade_type.upper()} TRADE BID: {open_bar}")

        if now > out_time:
            logger.warning(f"SELLING {trade_type.upper()} for time")

            order_tasks.place_order.delay(int(option_id), int(order_id), "SELL", 1)
            cache.set(f"s2_{trade_type}", 0, 1)

        if (
            last_closed_bar.high > price * momentum_threshold
            and prices_service.momentum_is_lost(last_closed_bar, 1)
        ):
            logger.warning(f"SELLING {trade_type.upper()} with profit STRAT 2")

            order_tasks.place_order.delay(int(option_id), int(order_id), "SELL", 1)
            cache.set(f"s2_{trade_type}", 0, 1)
