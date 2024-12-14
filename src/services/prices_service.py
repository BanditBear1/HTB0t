from sqlalchemy.orm import Session
from ib_insync import Contract, IB, BarDataList, BarData
import math
from typing import List
from src.models.models import PriceBar
from datetime import date, datetime, timedelta
from pytz import timezone
from src.models import schemas


def get_latest_price(
    contract: Contract, ib: IB, data_type: str = "LAST", allow_hist: bool = True
):
    market_data = ib.reqMktData(contract, "", False, False)

    cur_iter = 0

    while (market_data.last is None or math.isnan(market_data.last)) and cur_iter < 20:
        ib.sleep(0.1)
        cur_iter += 1

    if cur_iter == 20:
        if allow_hist:
            # Request historical data as fallback
            data_req = "TRADES" if data_type == "LAST" else data_type
            historical_data = ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="1 D",
                barSizeSetting="15 mins",
                whatToShow=data_req,
                useRTH=False,
            )
            if historical_data:
                return historical_data[-1].close  # Return last close price

        raise ValueError("Could not get latest price.")

    if data_type == "BID":
        return market_data.bid

    if data_type == "ASK":
        return market_data.ask

    return market_data.last


def get_historical_bars(
    ib: IB,
    contract: Contract,
    whatToShow: str,
    endDateTime: str = "",
    durationStr: str = "1 D",
    barSizeSetting: str = "1 min",
    useRTH: bool = False,
    formatDate: int = 1,
) -> BarDataList:
    return ib.reqHistoricalData(
        contract,
        endDateTime=endDateTime,
        durationStr=durationStr,  # Example: 1 day of data
        barSizeSetting=barSizeSetting,  # Example: 1-minute bars
        whatToShow=whatToShow,  # Request bid/ask data
        useRTH=useRTH,  # Whether to show regular trading hours data
        formatDate=formatDate,
    )


def check_bar_exists(
    db: Session,
    date: date,
    contract_id: str,
    contract_type: str,
    data_type: str,
    bar_size: int,
) -> PriceBar:
    return (
        db.query(PriceBar)
        .filter(
            # (
            #     PriceBar.stock_contract_id == contract_id
            #     if contract_type == "Stock"
            #     else None
            # ),
            # (
            #     PriceBar.option_contract_id == contract_id
            #     if contract_type == "Option"
            #     else None
            # ),
            PriceBar.contract_id == contract_id,
            # PriceBar.contract_type == contract_type,
            PriceBar.date == date,
            PriceBar.data_type == data_type,
            PriceBar.bar_size == bar_size,
        )
        .first()
    )


def get_add_price_bars(
    ib: IB,
    contract: Contract,
    data_type: str,
    contract_id: str,
    contract_type: str,
    bar_size: int,
    bars_to_create: List,
    db: Session,
    get_open_bar: bool = False,
):
    # First we check the last bar's date
    last_bar = db.query(PriceBar).filter(
        PriceBar.bar_size == bar_size,
        PriceBar.data_type == data_type,
        PriceBar.contract_id == contract_id,
    )

    durationStr = "1 D"

    if contract_type in ["Stock", "Index", "Forex", "Future"]:
        durationStr = "10 D"

    last_bar = last_bar.order_by(PriceBar.date.desc()).first()

    if last_bar:
        difference = datetime.now(timezone("America/New_York")) - last_bar.date
        difference_insec = (
            difference.total_seconds() + timedelta(minutes=bar_size).total_seconds()
        )

        if difference_insec < 3600:
            durationStr = f"{math.ceil(difference_insec / 60)} S"
        else:
            durationStr = f"{math.ceil(difference_insec / 3600 / 6.5)} D"

    open_bar = None

    for bar in get_historical_bars(
        ib,
        contract,
        data_type,
        durationStr=durationStr,
        barSizeSetting=f"{bar_size} mins",
    ):
        # We create the bars to add to the db
        if bar.date + timedelta(minutes=bar_size) > datetime.now(
            timezone("America/New_York")
        ):
            open_bar = bar
            continue

        if check_bar_exists(
            db, bar.date, contract_id, contract_type, data_type, bar_size
        ):
            continue

        bars_to_create.append(
            PriceBar(
                contract_id=contract_id,
                date=bar.date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                bar_size=bar_size,
                data_type=data_type,
            )
        )

    if get_open_bar:
        return [bars_to_create, open_bar]

    return bars_to_create


def get_price_bars_from_db(
    db: Session,
    contract_id: str,
    data_type: str,
    bar_size: int,
    order: str,
    limit: int,
) -> List[PriceBar]:
    query = (
        db.query(PriceBar)
        .filter(
            PriceBar.data_type == data_type,
            PriceBar.bar_size == bar_size,
            PriceBar.contract_id == contract_id,
        )
        .order_by(PriceBar.date.desc() if order == "desc" else PriceBar.date.asc())
    )

    return query.all()[:limit]


# Function to check if momentum is lost
def momentum_is_lost(
    last_closed_bar: schemas.PriceBar,
    direction: int = 1,
):
    body_indicator = last_closed_bar.close - last_closed_bar.open
    body_size = abs(body_indicator)

    if direction == 1 and body_indicator < 0 or direction == -1 and body_indicator > 0:
        # We either have a green bar when we are short or a red bar when we are long
        return True

    high_low = last_closed_bar.high if direction == 1 else last_closed_bar.low
    wick = abs(high_low - last_closed_bar.close)

    if wick > body_size * 2:
        return True

    return False
