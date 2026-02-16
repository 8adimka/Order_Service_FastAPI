import time

from celery import Celery

from .config import settings

celery = Celery(
    "tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


@celery.task
def process_order(order_id: str):
    time.sleep(2)
    print(f"Order {order_id} processed")
