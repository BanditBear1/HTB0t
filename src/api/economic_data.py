from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.responses import Response
from models import schemas, models
from models.database import get_db
from sqlalchemy.orm import Session
from services import prices_service
import celery.exceptions
import asyncio
from datetime import datetime, date, timezone, timedelta
from tasks import stocks_tasks
from typing import List

router = APIRouter()
