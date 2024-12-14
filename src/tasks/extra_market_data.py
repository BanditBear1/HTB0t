# from celery_app import celery_app
# import os
# from fastapi import Depends
# from sqlalchemy.orm import Session
# from models.database import get_celery_db
# from services import (
#     calendar_service,
#     prices_service,
#     ibapi_service,
#     contracts_service,
#     cache,
# )
# import asyncio
# import json
# from services import cache
# from models.models import Stock, PriceBar, Future, Option, Forex, Index
# from models import schemas
# import psutil
# from datetime import datetime, timedelta
# from ib_insync import (
#     Stock as ib_stock,
#     Option as ib_option,
#     ContFuture as ib_future,
#     Forex as ib_forex,
#     Index as ib_index,
#     RealTimeBarList,
#     BarData,
# )
# from pytz import timezone
# from tasks import trend_tasks, order_tasks, stocks_tasks


# entry_time = datetime.strptime("10:30:00", "%H:%M:%S").time()
# out_time = datetime.strptime("15:00:00", "%H:%M:%S").time()


# @celery_app.task
# def get_market_data():
#     # First we get the 0dte
#     expiration_date = calendar_service.get_0dte_expiration_date()
#     print(f"Expiration date: {expiration_date}")

#     # We connect to IB to get the option contracts
#     with ibapi_service.connect_to_ib() as ib:
#         # We fetch the Stock to check
#         with get_celery_db() as db:
#             stocks = db.query(Stock).filter(Stock.to_trade == True).all()

#             for stock in stocks:
#                 underlying = ib_stock(
#                     stock.symbol, stock.exchange, stock.currency, conId=stock.conId
#                 )
#                 # We check if the 0dte options are in the db already
#                 db_option_contracts = contracts_service.get_db_option_contracts(
#                     db, stock.id, expiration_date
#                 )

#                 if not db_option_contracts:
#                     # Request market data for underlying
#                     latest_price = prices_service.get_latest_price(underlying, ib)

#                     # Get the option contracts
#                     option_contracts = contracts_service.get_ib_option_contracts(
#                         ib,
#                         underlying,
#                         expiration_date,
#                         latest_price,
#                         stock.spread_around_spot,
#                     )

#                     # We add the option contracts to the db
#                     option_contracts = (
#                         contracts_service.save_ib_contracts_to_db_and_convert(
#                             option_contracts, stock.id, db
#                         )
#                     )

#                 else:
#                     # We get the IB contracts
#                     option_contracts = contracts_service.db_to_ib_option_contracts(
#                         db_option_contracts
#                     )

#                 for option_contract in option_contracts:
#                     get_price_data.delay(
#                         option_contract.db_id,
#                         "Option",
#                         option_contract.option.symbol,
#                         option_contract.option.exchange,
#                         option_contract.option.currency,
#                         1,
#                         None,
#                         option_contract.option.lastTradeDateOrContractMonth,
#                         option_contract.option.strike,
#                         option_contract.option.right,
#                     )

#                 get_price_data.delay(
#                     stock.id,
#                     "Stock",
#                     stock.symbol,
#                     stock.exchange,
#                     stock.currency,
#                     1,
#                     stock.conId,
#                 )

#             futures = db.query(Future).all()

#             for future in futures:
#                 get_price_data.delay(
#                     future.id,
#                     "Future",
#                     future.symbol,
#                     future.exchange,
#                     future.currency,
#                     1,
#                 )

#             forex = db.query(Forex).all()

#             for forex_pair in forex:
#                 get_price_data.delay(
#                     forex_pair.id,
#                     "Forex",
#                     forex_pair.symbol,
#                     forex_pair.exchange,
#                     forex_pair.currency,
#                     1,
#                 )

#             indexes = db.query(Index).all()

#             for index in indexes:
#                 get_price_data.delay(
#                     index.id,
#                     "Index",
#                     index.symbol,
#                     index.exchange,
#                     index.currency,
#                     1,
#                 )


# @celery_app.task
# def get_price_data(
#     contract_db_id: str,
#     contract_type: str,
#     symbol: str,
#     exchange: str,
#     currency: str,
#     bar_size: int = 1,
#     conId: int = None,
#     lastTradeDateOrContractMonth: str = None,
#     strike: float = None,
#     right: str = None,
# ):
#     data_types = ["BID", "ASK", "TRADES"]

#     if contract_type == "Stock":
#         contract = ib_stock(symbol, exchange, currency, conId=conId)

#     elif contract_type == "Option":
#         contract = ib_option(
#             symbol, lastTradeDateOrContractMonth, strike, right, exchange, currency
#         )

#         if (
#             lastTradeDateOrContractMonth < datetime.now().strftime("%Y%m%d")
#             or datetime.now(timezone("America/New_York")).time()
#             < datetime.strptime("09:30:00", "%H:%M:%S").time()
#         ):
#             # We only want to collect for 0dte options that are not expired
#             return

#     elif contract_type == "Future":
#         contract = ib_future(symbol, exchange)

#     elif contract_type == "Forex":
#         contract = ib_forex(symbol)
#         data_types = ["ASK", "BID"]

#     elif contract_type == "Index":
#         contract = ib_index(symbol, exchange)

#     with ibapi_service.connect_to_ib() as ib:
#         with get_celery_db() as db:
#             bars_to_create = []

#             for data_type in data_types:
#                 bars_to_create = prices_service.get_add_price_bars(
#                     ib,
#                     contract,
#                     data_type,
#                     contract_db_id,
#                     contract_type,
#                     bar_size,
#                     bars_to_create,
#                     db,
#                 )
#             # We add the bars to the db
#             db.add_all(bars_to_create)
#             db.commit()


# # def stream_asset(
# #     contract_type: str,
# #     symbol: str,
# #     exchange: str,
# #     currency: str,
# #     data_type: str,
# #     right: str = None,
# #     strike: float = None,
# #     lastTradeDateOrContractMonth: str = None,
# #     last_open_bar: PriceBar = None,
# # ):
# #     if contract_type == "Stock":
# #         contract = ib_stock(symbol, exchange, currency)
# #     elif contract_type == "Option":
# #         contract = ib_option(
# #             symbol, lastTradeDateOrContractMonth, strike, right, exchange, currency
# #         )

# #     def onBarUpdate(bars: RealTimeBarList, hasNewBar):
# #         cache.set(f"streaming_{contract_type}_{symbol}_{data_type}", True, 10)
# #         print(bars, hasNewBar)

# #     with ibapi_service.connect_to_ib() as ib:
# #         ib.reqRealTimeBars(contract, 1, data_type, False)
# #         ib.barUpdateEvent += onBarUpdate

# #         try:
# #             ib.run()
# #         except KeyboardInterrupt:
# #             ib.disconnect()
# #             print("Disconnected")


# @celery_app.task
# def stream_spx_trades():
#     trade_info: str = cache.get("trade")
#     if not trade_info:
#         return

#     trade = int(trade_info.split(":")[0])
#     is_sl = trade_info.split(":")[1] == "SL"

#     if is_sl:
#         return

#     # First we get the past data
#     with get_celery_db() as db:
#         spx = db.query(Index).filter(Index.symbol == "SPX").first()

#         spx_contract = ib_index("SPX", "CBOE")

#         with ibapi_service.connect_to_ib() as ib:
#             spx_contract = ib.qualifyContracts(spx_contract)[0]

#             bars, open_bar = prices_service.get_add_price_bars(
#                 ib,
#                 spx_contract,
#                 "TRADES",
#                 spx.id,
#                 "Index",
#                 15,
#                 [],
#                 db,
#                 True,
#             )

#         if bars:
#             db.add_all(bars)
#             db.commit()

#     cache.set(
#         f"SPX_TRADE_15O",
#         schemas.PriceBar(
#             id=0,
#             date=open_bar.date,
#             open=open_bar.open,
#             high=open_bar.high,
#             low=open_bar.low,
#             close=open_bar.close,
#             volume=open_bar.volume,
#         ).model_dump_json(),
#         60 * 20,
#     )

#     # Now we check to enter:
#     logger.warning(f"SPX last price: {open_bar.close}")

#     # Are we in the money?
#     sl_trigger = cache.get("stop_loss_trigger")

#     if (
#         trade == 1
#         and open_bar.close < sl_trigger
#         or (trade == -1 and open_bar.close > sl_trigger)
#     ):
#         logger.warning("Exiting STOP LOSS SPX")

#         sell_trade_info: str = cache.get("sell_trade")
#         if not sell_trade_info:
#             return

#         order_id = int(sell_trade_info.split(":")[0])
#         sell_trade = int(sell_trade_info.split(":")[1])

#         order_tasks.place_order.delay(sell_trade, order_id, "BUY", 1)

#         # We update the cache
#         cache.set(f"trade", f"{trade}:SL")

#         # We update the high/low cache for the next trade
#         if trade == 1 and open_bar.high > cache.get(f"SPX_TRADES_high"):
#             cache.set(f"SPX_TRADES_high", open_bar.high)

#         elif trade == -1 and open_bar.low < cache.get(f"SPX_TRADES_low"):
#             cache.set(f"SPX_TRADES_low", open_bar.low)
