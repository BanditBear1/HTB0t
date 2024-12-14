from ib_insync import (
    IB,
    Contract,
    Option,
    ContractDetails,
    OptionChain,
    Stock,
    ContFuture,
    Forex,
    Index,
)
from sqlalchemy.orm import Session
from datetime import date
from src.models import models
from src.models.schemas import IBOptionWithID, Contract as schemasContract
from typing import List, Optional
from fastapi import HTTPException
from pytz import timezone
from datetime import datetime
from src.services import prices_service, contracts_service, ibapi_service, calendar_service
from src.tasks import stocks_tasks


def get_contract_details(ib: IB, contract: Contract) -> List[ContractDetails]:
    contract_details = ib.reqContractDetails(contract)

    if not contract_details:
        raise ValueError("Contract details not found.")

    return contract_details


def get_option_chains(ib: IB, underlying: Contract) -> List[OptionChain]:
    chains = ib.reqSecDefOptParams(
        underlying.symbol, "", underlying.secType, underlying.conId
    )

    if not chains:
        raise ValueError("Option chains not found.")

    return chains


def get_db_option_contracts(
    db: Session,
    underlying_id: int,
    expiration_date: date,
) -> List[models.Option]:
    return (
        db.query(models.Option)
        .filter(
            models.Option.underlying_id == underlying_id,
            models.Option.lastTradeDateOrContractMonth == expiration_date,
            # models.Option.underlying_type == underlying_type,
        )
        .all()
    )


def get_ib_option_contracts(
    ib: IB,
    underlying: Contract,
    expiration_date: date,
    latest_price: float,
    spread_around_spot: float,
) -> List[Option]:
    chains = get_option_chains(ib, underlying)

    if underlying.symbol == "SPX":
        chain = [
            chain
            for chain in chains
            if chain.exchange == "SMART" and chain.tradingClass == "SPXW"
        ][0]
    else:
        chain = [chain for chain in chains if chain.exchange == "SMART"][0]

    if expiration_date not in chain.expirations:
        raise ValueError("Expiration date not found in chain.")

    # Filter strikes around the spot price
    # We only want to fetch data for strikes that are within a certain range around the spot price
    strikes_to_fetch = [
        strike
        for strike in chain.strikes
        if strike > latest_price - spread_around_spot
        and strike < latest_price + spread_around_spot
    ]

    # Get all strikes for this expiration and create option contracts
    option_contracts = []
    for strike in strikes_to_fetch:
        for right in ["C", "P"]:  # Call and Put options
            contract = Option(
                symbol=underlying.symbol,
                lastTradeDateOrContractMonth=expiration_date,
                strike=strike,
                right=right,
                exchange="SMART",
            )
            option_contracts.append(contract)

    return option_contracts


def db_to_ib_option_contracts(
    option_contracts: List[models.Option],
) -> List[IBOptionWithID]:
    return [
        IBOptionWithID(
            option=Option(
                symbol=contract.symbol,
                lastTradeDateOrContractMonth=contract.lastTradeDateOrContractMonth.strftime(
                    "%Y%m%d"
                ),
                strike=contract.strike,
                right=contract.right,
                exchange=contract.exchange,
                currency=contract.currency,
            ),
            db_id=contract.id,
        )
        for contract in option_contracts
    ]


def save_ib_contracts_to_db_and_convert(
    option_contracts: List[Option],
    underlying_id: int,
    db: Session = None,
) -> List[models.Option]:
    db_contracts = [
        models.Option(
            symbol=contract.symbol,
            contract_type="Option",
            lastTradeDateOrContractMonth=contract.lastTradeDateOrContractMonth,
            strike=contract.strike,
            right=contract.right,
            exchange=contract.exchange,
            currency=contract.currency,
            underlying_id=underlying_id,
        )
        for contract in option_contracts
    ]

    if db:
        # print("Adding contracts to the db")
        # print(f"Contracts: {db_contracts}")
        # print(f"Original: {option_contracts}")
        db.add_all(db_contracts)
        db.commit()

        for db_contract in db_contracts:
            db.refresh(db_contract)

    return [
        IBOptionWithID(
            option=Option(
                symbol=contract.symbol,
                lastTradeDateOrContractMonth=contract.lastTradeDateOrContractMonth.strftime(
                    "%Y%m%d"
                ),
                strike=contract.strike,
                right=contract.right,
                exchange=contract.exchange,
                currency=contract.currency,
            ),
            db_id=contract.id,
        )
        for contract in db_contracts
    ]


def get_any_contracts(db: Session, contract_type: str):
    if contract_type == "Stock":
        return db.query(models.Stock).all()
    elif contract_type == "Option":
        return db.query(models.Option).all()
    elif contract_type == "Future":
        return db.query(models.Future).all()
    elif contract_type == "Forex":
        return db.query(models.Forex).all()
    elif contract_type == "Index":
        return db.query(models.Index).all()
    else:
        raise HTTPException(status_code=400, detail="Invalid contract type")


def check_contract_exist(db: Session, contract: schemasContract, contract_type: str):
    model = None
    if contract_type == "Stock":
        model = models.Stock
    elif contract_type == "Option":
        model = models.Option
    elif contract_type == "Future":
        model = models.Future
    elif contract_type == "Forex":
        model = models.Forex
    elif contract_type == "Index":
        model = models.Index
    else:
        raise HTTPException(status_code=400, detail="Invalid contract type")

    return (
        db.query(model)
        .filter(
            model.symbol == contract.symbol,
            model.exchange == contract.exchange,
            model.currency == contract.currency,
            model.to_trade == contract.to_trade,
        )
        .first()
    )


def get_contract_by_id(db: Session, contract_id: int, contract_type: str):
    model = None
    if contract_type == "Stock":
        model = models.Stock
    elif contract_type == "Option":
        model = models.Option
    elif contract_type == "Future":
        model = models.Future
    elif contract_type == "Forex":
        model = models.Forex
    elif contract_type == "Index":
        model = models.Index
    else:
        raise HTTPException(status_code=400, detail="Invalid contract type")

    return db.query(model).filter(model.id == contract_id).first()


def get_contract_by_symbol(db: Session, symbol: str, contract_type: str):
    model = None
    if contract_type == "Stock":
        model = models.Stock
    elif contract_type == "Option":
        model = models.Option
    elif contract_type == "Future":
        model = models.Future
    elif contract_type == "Forex":
        model = models.Forex
    elif contract_type == "Index":
        model = models.Index
    else:
        raise HTTPException(status_code=400, detail="Invalid contract type")

    return db.query(model).filter(model.symbol == symbol).first()


# Helper function to create the appropriate IB contract object
def create_ib_contract(
    contract_type: str,
    symbol: str,
    exchange: str,
    currency: str,
    conId: Optional[int] = None,
    lastTradeDateOrContractMonth: Optional[str] = None,
    strike: Optional[float] = None,
    right: Optional[str] = None,
):
    if contract_type == "Stock":
        return Stock(symbol, exchange, currency, conId=conId)

    if contract_type == "Option":
        if (
            lastTradeDateOrContractMonth < datetime.now().strftime("%Y%m%d")
            or datetime.now(timezone("America/New_York")).time()
            < datetime.strptime("09:30:00", "%H:%M:%S").time()
        ):
            return None  # Skip expired or pre-market 0DTE options
        return Option(
            symbol, lastTradeDateOrContractMonth, strike, right, exchange, currency
        )

    if contract_type == "Future":
        return ContFuture(symbol, exchange)

    if contract_type == "Forex":
        return Forex(symbol)

    if contract_type == "Index":
        return Index(symbol, exchange)

    return None


def get_fetch_option_contracts_with_strike(
    db: Session, ib: IB, underlying_id: int, expiration_date: date, trend: int = None
):
    underlying_db_contact: models.BaseContract = db.query(models.BaseContract).get(
        underlying_id
    )
    contracts = (
        db.query(models.Option)
        .filter(
            models.Option.underlying_id == underlying_id,
            models.Option.lastTradeDateOrContractMonth == expiration_date,
        )
        .all()
    )

    if underlying_db_contact.contract_type == "Stock":
        underlying_contract = Stock(
            underlying_db_contact.symbol,
            underlying_db_contact.exchange,
            underlying_db_contact.currency,
        )

    elif underlying_db_contact.contract_type == "Index":
        underlying_contract = Index(
            underlying_db_contact.symbol, underlying_db_contact.exchange
        )

    underlying_contract = ib.qualifyContracts(underlying_contract)[0]
    latest_price = prices_service.get_latest_price(underlying_contract, ib)

    if not contracts:
        # Get the option contracts
        option_contracts = contracts_service.get_ib_option_contracts(
            ib,
            underlying_contract,
            expiration_date,
            latest_price,
            150,
        )

        # We add the option contracts to the db
        contracts_service.save_ib_contracts_to_db_and_convert(
            option_contracts, underlying_id, db
        )

    contracts = db.query(models.Option).filter(
        models.Option.underlying_id == underlying_id,
        models.Option.lastTradeDateOrContractMonth == expiration_date,
    )

    if not trend:
        return contracts.all()

    elif trend == 1:
        # We buy puts out of money
        contracts = (
            contracts.filter(
                models.Option.right == "P",
                models.Option.strike < latest_price,
            )
            .order_by(models.Option.strike.desc())
            .all()
        )

    else:
        # We buy calls out of money
        contracts = (
            contracts.filter(
                models.Option.right == "C",
                models.Option.strike > latest_price,
            )
            .order_by(models.Option.strike.asc())
            .all()
        )

    return contracts


def get_create_spy(db: Session):
    stock = db.query(models.Stock).filter(models.Stock.symbol == "SPY").first()
    if not stock:
        stocks_tasks.fetch_stock("SPY", "ARCA", "USD", True)
        spx = db.query(models.Index).filter(models.Index.symbol == "SPX").first()

        if not spx:
            stocks_tasks.fetch_index("SPX", "CBOE", "USD", True)
            spx = db.query(models.Stock).filter(models.Stock.symbol == "SPY").first()

            with ibapi_service.connect_to_ib() as ib:
                expiration_date = calendar_service.get_0dte_expiration_date()
                contracts = get_fetch_option_contracts_with_strike(
                    db, ib, spx.id, expiration_date
                )

    return stock
