from models import models, schemas
from fastapi import HTTPException, Depends, Header, Cookie
import os
from datetime import datetime, timedelta, timezone
import os
from sqlalchemy.orm import Session, joinedload
import json
from services import contracts_service
from typing import List


def get_option_expiration_dates(db: Session, symbol: str) -> List[str]:
    """
    Retrieves distinct option expiration dates for a given stock symbol.

    Args:
        db (Session): Database session.
        symbol (str): The stock symbol to retrieve expiration dates for.

    Returns:
        List[str]: A list of expiration dates in 'YYYYMMDD' format.

    Raises:
        HTTPException: If the stock is not found.
    """
    # Get the stock contract by symbol
    stock = contracts_service.get_contract_by_symbol(db, symbol, "Stock")
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Query distinct expiration dates from options tied to the stock
    expiration_dates = (
        db.query(models.Option.lastTradeDateOrContractMonth)
        .filter(models.Option.underlying_id == stock.id)
        .distinct()
    )

    # Convert dates to 'YYYYMMDD' string format and return them as a list
    return [date[0].strftime("%Y%m%d") for date in expiration_dates]


def get_options_strikes(db: Session, symbol: str, expiration_date: str) -> List[float]:
    """
    Retrieves distinct strike prices for options of a given stock symbol and expiration date.

    Args:
        db (Session): Database session.
        symbol (str): The stock symbol to retrieve strikes for.
        expiration_date (str): The expiration date to filter strikes by.

    Returns:
        List[float]: A list of distinct strike prices.

    Raises:
        HTTPException: If the stock is not found.
    """
    # Get the stock contract by symbol
    stock = contracts_service.get_contract_by_symbol(db, symbol, "Stock")
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Query distinct strike prices for the given stock and expiration date
    strikes = (
        db.query(models.Option.strike)
        .filter(
            models.Option.underlying_id == stock.id,
            models.Option.lastTradeDateOrContractMonth == expiration_date,
        )
        .distinct()
        .order_by(models.Option.strike)
    )

    # Return the list of strikes
    return [strike[0] for strike in strikes]


def get_option_contract_db(
    db: Session, symbol: str, expiration_date: str, strike: float, right: str
) -> models.Option:
    """
    Retrieves a specific option contract based on symbol, expiration date, strike price, and right (CALL/PUT).

    Args:
        db (Session): Database session.
        symbol (str): The stock symbol.
        expiration_date (str): The expiration date of the option.
        strike (float): The strike price of the option.
        right (str): The option type (CALL/PUT).

    Returns:
        models.Option: The corresponding option contract.

    Raises:
        HTTPException: If the stock is not found.
    """
    # Get the stock contract by symbol
    stock = contracts_service.get_contract_by_symbol(db, symbol, "Stock")
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Query the option contract with the given parameters
    option = (
        db.query(models.Option)
        .filter(
            models.Option.underlying_id == stock.id,
            models.Option.lastTradeDateOrContractMonth == expiration_date,
            models.Option.strike == strike,
            models.Option.right == right,  # Option type (CALL or PUT)
        )
        .first()  # Return the first matching option
    )

    return option
