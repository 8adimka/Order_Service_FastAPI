import logging
import time
import uuid

from celery import Celery

from .config import settings

logger = logging.getLogger(__name__)

celery = Celery(
    "tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


@celery.task(bind=True, max_retries=3)
def process_order(self, order_id: str):
    """
    Обработка заказа:
    1. Имитация обработки платежа
    2. Обновление статуса в БД на PAID

    Args:
        order_id: ID заказа для обработки
    """
    from . import crud, models
    from .database import SessionLocal

    db = SessionLocal()
    try:
        logger.info(f"Starting to process order {order_id}")

        # Имитация обработки платежа (2 секунды)
        time.sleep(2)

        # Преобразуем строку в UUID
        try:
            order_uuid = uuid.UUID(order_id)
        except ValueError:
            logger.error(f"Invalid order_id format: {order_id}")
            raise Exception(f"Invalid order_id format: {order_id}")

        # Обновляем статус заказа на PAID в БД
        updated_order = crud.update_order_status(
            db, order_uuid, models.OrderStatus.PAID
        )

        if updated_order:
            logger.info(f"Order {order_id} successfully updated to PAID status")
            return {
                "order_id": str(updated_order.id),
                "status": updated_order.status.value,
                "message": "Order processed successfully",
            }
        else:
            logger.error(f"Order {order_id} not found in database")
            raise Exception(f"Order {order_id} not found in database")

    except Exception as e:
        logger.error(f"Error processing order {order_id}: {str(e)}")
        # Retry с exponential backoff (2^retries seconds)
        raise self.retry(exc=e, countdown=2**self.request.retries)
    finally:
        db.close()
