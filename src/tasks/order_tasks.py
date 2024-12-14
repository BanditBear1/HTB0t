from celery_app import celery_app
from models import models
from models.database import get_celery_db
from services import (
    prices_service,
    contracts_service,
    ibapi_service,
    calendar_service,
    cache,
    notification_service,
)

from ib_insync import LimitOrder


@celery_app.task
def enter_trade(trend: int):
    # First we get all the contracts for SPX
    expiration_date = calendar_service.get_0dte_expiration_date()
    entry_prices = {}

    with get_celery_db() as db:
        spx_contract: models.Index = contracts_service.get_contract_by_symbol(
            db, "SPX", "Index"
        )

        with ibapi_service.connect_to_ib() as ib:
            contracts = contracts_service.get_fetch_option_contracts_with_strike(
                db, ib, spx_contract.id, expiration_date, trend
            )

            money_contract = contracts[1]
            place_order.delay(
                money_contract.id, None, "SELL", 1, trend=trend, cache_key="sell_trade"
            )
            entry_prices[money_contract.id] = prices_service.get_last_price(ib, money_contract)

            saver_contract = contracts[9]
            place_order.delay(
                saver_contract.id,
                None,
                "BUY",
                1,
                trend=trend,
                cache_key="buy_trade",
            )
            entry_prices[saver_contract.id] = prices_service.get_last_price(ib, saver_contract)

            cache.set(f"trade", f"{trend}:0")
            
            # Send trade entry notification
            message = notification_service.format_trade_entry_message(
                trend, [money_contract, saver_contract], entry_prices
            )
            notification_service.send_email_notification("Trade Entry", message)

            # cache.set(f"stop_loss_trigger", money_contract.strike)


@celery_app.task
def enter_strat_2(direction: int):
    expiration_date = calendar_service.get_0dte_expiration_date()

    with get_celery_db() as db:
        spx_contract: models.Index = contracts_service.get_contract_by_symbol(
            db, "SPX", "Index"
        )

        with ibapi_service.connect_to_ib() as ib:
            contracts = contracts_service.get_fetch_option_contracts_with_strike(
                db, ib, spx_contract.id, expiration_date, -direction
            )

        if direction == 1:
            cache_key = "s2_call"
            contract = contracts[14]
        else:
            cache_key = "s2_put"
            contract = contracts[21]

        place_order.delay(
            contract.id, None, "BUY", 1, trend=direction, cache_key=cache_key
        )


@celery_app.task
def place_order(
    option_id: int,
    order_id: int,
    order_type: str = "BUY",
    size: int = 1,
    re_enter: bool = False,
    trend: int = None,  # Is defined when entering the trade
    cache_key: str = None,
):
    with get_celery_db() as db:
        with ibapi_service.connect_to_ib() as ib:
            contract = db.query(models.Option).get(option_id)
            ib_contract = contracts_service.db_to_ib_option_contracts([contract])[
                0
            ].option

            ib_contract = ib.qualifyContracts(ib_contract)[0]

            bid_ask = "ASK" if order_type == "BUY" else "BID"

            contract_price = prices_service.get_latest_price(ib_contract, ib, bid_ask)
            contract_price = round(contract_price, 2)

            order = LimitOrder(order_type, 1, contract_price)
            trade = ib.placeOrder(ib_contract, order)

            ib.sleep(2)

            # print(trade)

            if not order_id:
                # We get the bid as bid_ask_opposite_price if we bought
                # We get the ask as bid_ask_opposite_price if we sold
                bid_ask_opposite = "BID" if order_type == "BUY" else "ASK"
                bid_ask_opposite_price = prices_service.get_latest_price(
                    ib_contract, ib, bid_ask_opposite
                )

        if not order_id:
            # This mean we just opened a trade
            order = models.Order(
                contract_id=option_id,
                direction=trend,
                order_type=order_type,
                order_price=contract_price,
                order_size=1,
                bid_at_entry=(
                    bid_ask_opposite_price if order_type == "BUY" else contract_price
                ),
                ask_at_entry=(
                    contract_price if order_type == "BUY" else bid_ask_opposite_price
                ),
            )

            db.add(order)

            db.commit()
            db.refresh(order)

            cache.set(cache_key, f"{order.id}:{option_id}:{contract_price}")

            print(
                f"""Order placed with contract:
price: {contract_price}, size: {size} | contract: {ib_contract.right} {ib_contract.strike} {ib_contract.lastTradeDateOrContractMonth}"""
            )

        else:
            # This mean we just closed a trade
            db_trade: models.Order = db.query(models.Order).get(order_id)
            db_trade.order_exit_price = contract_price

            db.commit()

            print(
                f"""Order placed with contract:
price: {contract_price}, size: {size} | contract: {ib_contract.right} {ib_contract.strike} {ib_contract.lastTradeDateOrContractMonth}
pnl: {contract_price - db_trade.order_price}"""
            )

    if re_enter:
        # We re-enter the trade with the same strategy
        enter_trade.delay(db_trade.direction)
