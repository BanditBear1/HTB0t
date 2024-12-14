from celery_app import celery_app
import os
from fastapi import Depends
from sqlalchemy.orm import Session
from models.database import get_celery_db
from services import calendar_service, prices_service, ibapi_service, contracts_service
import asyncio
import json
from services import cache
from models.models import Stock, Index
from ib_insync import Stock as ib_stock, Index as ib_index


@celery_app.task
def fetch_stock(symbol: str, exchange: str, currency: str, to_trade: bool):
    with ibapi_service.connect_to_ib() as ib:
        stock = ib_stock(symbol, exchange, currency)

        contract_details = contracts_service.get_contract_details(ib, stock)
        conId = contract_details[0].contract.conId

        with get_celery_db() as db:
            db_stock = Stock(
                symbol=symbol,
                contract_type="Stock",
                exchange=exchange,
                currency=currency,
                conId=conId,
                to_trade=to_trade,
            )
            db.add(db_stock)
            db.commit()
            db.refresh(db_stock)


@celery_app.task
def fetch_index(symbol: str, exchange: str, currency: str, to_trade: bool):
    with ibapi_service.connect_to_ib() as ib:
        index = ib_index(symbol, exchange)

        contract_details = contracts_service.get_contract_details(ib, index)

        with get_celery_db() as db:
            db_index = Index(
                symbol=symbol,
                contract_type="Index",
                exchange=exchange,
                currency=currency,
                to_trade=to_trade,
            )
            db.add(db_index)
            db.commit()
            db.refresh(db_index)
