from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    Float,
    DateTime,
    Date,
    Enum,
    JSON,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from enum import Enum as PyEnum
import json
import uuid
from typing import List, Dict, Any, Optional
from src.models.database import Base


class BaseContract(Base):
    # __abstract__ = True  # This base class will not have its own table
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="USD")
    contract_type: Mapped[str] = mapped_column(String)  # polymorphic column

    to_trade: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    __mapper_args__ = {"polymorphic_on": "contract_type"}  # polymorphic discriminator


class Stock(BaseContract):
    # __tablename__ = "stocks"

    conId: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)

    spread_around_spot: Mapped[float | None] = mapped_column(
        Float, default=2, nullable=True
    )

    __mapper_args__ = {
        "polymorphic_identity": "Stock",  # defines this class as 'Stock'
    }


class Option(BaseContract):
    # __tablename__ = "options"

    lastTradeDateOrContractMonth: Mapped[datetime | None] = mapped_column(
        Date, nullable=True
    )
    strike: Mapped[float | None] = mapped_column(Float, nullable=True)
    right: Mapped[str | None] = mapped_column(String, nullable=True)

    underlying_id: Mapped[int | None] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), nullable=True
    )
    underlying: Mapped[BaseContract] = relationship(
        "BaseContract"
    )  # references 'Stock' or 'Option'

    __mapper_args__ = {
        "polymorphic_identity": "Option",  # defines this class as 'Option'
    }


class Future(BaseContract):
    # __tablename__ = "futures"

    __mapper_args__ = {
        "polymorphic_identity": "Future",  # defines this class as 'Future'
    }


class Index(BaseContract):
    # __tablename__ = "indices"

    __mapper_args__ = {
        "polymorphic_identity": "Index",  # defines this class as 'Index'
    }


class Forex(BaseContract):
    # __tablename__ = "futures"

    __mapper_args__ = {
        "polymorphic_identity": "Forex",  # defines this class as 'Future'
    }


class PriceBar(Base):
    __tablename__ = "price_bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)
    bar_size: Mapped[int] = mapped_column(Integer)  # In minutes

    data_type: Mapped[str] = mapped_column(String)
    trend: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)

    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))
    contract: Mapped[BaseContract] = relationship(
        "BaseContract"
    )  # references 'Stock' or 'Option'

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class EconomicDataGroup(Base):
    __tablename__ = "economic_data_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    data_type: Mapped[str] = mapped_column(String)
    interval: Mapped[str] = mapped_column(String)
    unit: Mapped[str] = mapped_column(String)

    economic_data: Mapped["EconomicData"] = relationship(
        "EconomicData", back_populates="economic_data_group"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class EconomicData(Base):
    __tablename__ = "economic_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    value: Mapped[float] = mapped_column(Float)

    economic_data_group_id: Mapped[int] = mapped_column(
        ForeignKey("economic_data_groups.id", ondelete="CASCADE"), nullable=False
    )
    economic_data_group: Mapped[EconomicDataGroup] = relationship("EconomicDataGroup")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE")
    )
    contract: Mapped[BaseContract] = relationship("BaseContract")
    direction: Mapped[int] = mapped_column(Integer)  # 1/-1

    order_type: Mapped[str] = mapped_column(String)  # BUY/SELL
    order_size: Mapped[float] = mapped_column(Float)  # Quantity
    order_price: Mapped[float] = mapped_column(Float)  # Price
    order_status: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )  # OPEN/FILLED/CANCELLED

    order_exit_price: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None
    )

    bid_at_entry: Mapped[float] = mapped_column(Float)
    ask_at_entry: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
