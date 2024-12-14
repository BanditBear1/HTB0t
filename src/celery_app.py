from celery import Celery
import os
from datetime import datetime
from src.tasks import celeryconfig

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "market_data",
    broker=CELERY_BROKER_URL,
    backend=CELERY_BROKER_URL,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.update(
    task_queues=celeryconfig.CELERY_TASK_QUEUES,
    task_routes=celeryconfig.CELERY_TASK_ROUTES,
    beat_schedule=celeryconfig.CELERY_BEAT_SCHEDULE,
    broker_transport_options={'visibility_timeout': 43200},  # 12 hours
    redis_max_connections=20,
    broker_pool_limit=None,
)

celery_app.autodiscover_tasks(
    [
        "src.tasks.market_reader_tasks",
        "src.tasks.stocks_tasks",
        "src.tasks.trend_tasks",
        "src.tasks.economic_data_tasks",
    ],
    force=True,
)
