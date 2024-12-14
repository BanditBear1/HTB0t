# main.py
from fastapi import FastAPI, WebSocket, APIRouter, Depends
from services import cache
from models.database import get_db
from sqlalchemy.orm import Session
import json
import traceback
from starlette.websockets import WebSocketDisconnect
import asyncio
import time

router = APIRouter()


# Websocket endpoint
@router.websocket("/")
async def data_streaming_websocket(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    await websocket.accept()

    try:
        while True:
            # Receive messages from websocket (if needed)
            data_to_send = {
                "trend": cache.get("SPY_TRADES_trend"),
                "high": cache.get("SPY_TRADES_high"),
                "low": cache.get("SPY_TRADES_low"),
                "open_bar": cache.get("SPY_TRADE_15O"),
            }
            await websocket.send_text(json.dumps(data_to_send))
            await asyncio.sleep(30)

    except WebSocketDisconnect as e:
        # Handle WebSocket disconnect gracefully
        print(f"WebSocket connection closed with status code {e.code}: {e.reason}")
        websocket.close()

    finally:
        # Ensure the WebSocket is closed
        await websocket.close()
