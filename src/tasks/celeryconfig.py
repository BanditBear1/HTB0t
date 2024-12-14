from celery.schedules import crontab
from datetime import timedelta
from kombu import Exchange, Queue
import logging

CELERY_BEAT_SCHEDULE = {
    # "market_data_collector": {
    #     "task": "src.tasks.market_reader_tasks.get_market_data",
    #     "schedule": timedelta(minutes=10),  # Run every minute for testing purposes
    # },
    # "economic_data": {
    #     "task": "src.tasks.economic_data_tasks.get_inflation",
    #     "schedule": crontab(hour=9, minute=30),
    # },
    "check_streams": {
        "task": "src.tasks.market_reader_tasks.check_streams",
        "schedule": timedelta(seconds=30),  # Run every minute for testing purposes
    },
    # "cleanup_streams": {
    #     "task": "src.tasks.broadcasting_tasks.cleanup_streams",
    #     "schedule": timedelta(minutes=1),
    # },
}


CELERY_TASK_QUEUES = (
    Queue("default", Exchange("default"), routing_key="default"),
    # Queue("user_requests", Exchange("user_requests"), routing_key="user_requests"),
    # Queue("auto_collector", Exchange("auto_collector"), routing_key="auto_collector"),
    # Queue("broadcasting", Exchange("broadcasting"), routing_key="broadcasting"),
)

CELERY_TASK_ROUTES = {
    "src.tasks.market_reader_tasks.*": {"queue": "default"},
    "src.tasks.stocks_tasks.*": {"queue": "default"},
    "src.tasks.economic_data_tasks.*": {"queue": "default"},
    "src.tasks.trend_tasks.*": {"queue": "default"},
    "src.tasks.order_tasks.*": {"queue": "default"},
}

CELERY_LOG_LEVEL = logging.INFO
