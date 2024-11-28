from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import asyncio
import nest_asyncio
from pydantic import BaseModel

from src.services.ib_connection import IBConnection
from src.services.market_data import MarketDataService
from src.services.order_management import OrderManagementService

# Enable nested event loops for FastAPI + IB
nest_asyncio.apply()

app = FastAPI(title="HTB Integrated Trading System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class OrderRequest(BaseModel):
    symbol: str
    action: str
    quantity: float
    order_type: str
    price: Optional[float] = None

# Services
ib_connection = IBConnection()
market_data = MarketDataService(ib_connection)
order_mgmt = OrderManagementService(ib_connection)

@app.on_event("startup")
async def startup():
    """Connect to IB on startup"""
    await ib_connection.connect()

@app.on_event("shutdown")
async def shutdown():
    """Disconnect from IB on shutdown"""
    await ib_connection.disconnect()

# Market Data Endpoints
@app.get("/api/v1/market/stock/{symbol}")
async def get_stock_price(symbol: str):
    """Get current stock price"""
    try:
        price = await market_data.get_stock_price(symbol)
        return {"symbol": symbol, "price": price}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/market/options/{symbol}")
async def get_option_chain(symbol: str):
    """Get option chain for symbol"""
    try:
        chain = await market_data.get_option_chain(symbol)
        return {"symbol": symbol, "options": chain}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Order Management Endpoints
@app.post("/api/v1/orders")
async def place_order(order: OrderRequest):
    """Place a new order"""
    try:
        contract = await market_data.get_contract(order.symbol)
        
        if order.order_type == "market":
            result = await order_mgmt.place_market_order(
                contract=contract,
                action=order.action,
                quantity=order.quantity
            )
        elif order.order_type == "limit" and order.price:
            result = await order_mgmt.place_limit_order(
                contract=contract,
                action=order.action,
                quantity=order.quantity,
                limit_price=order.price
            )
        else:
            raise ValueError("Invalid order type or missing price")
            
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/v1/orders/{order_id}")
async def cancel_order(order_id: int):
    """Cancel an existing order"""
    try:
        success = await order_mgmt.cancel_order(order_id)
        if not success:
            raise HTTPException(status_code=404, detail="Order not found")
        return {"message": "Order cancelled successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/orders")
async def get_open_orders():
    """Get all open orders"""
    try:
        orders = await order_mgmt.get_open_orders()
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/positions")
async def get_positions():
    """Get current positions"""
    try:
        positions = await order_mgmt.get_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/portfolio")
async def get_portfolio():
    """Get portfolio summary"""
    try:
        portfolio = await order_mgmt.get_portfolio()
        return portfolio
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
