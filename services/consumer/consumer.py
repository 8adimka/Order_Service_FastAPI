import asyncio
import json
import logging
import os

from aiokafka import AIOKafkaConsumer
from celery import Celery

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Celery
celery_app = Celery(
    "consumer",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
)


async def consume():
    """
    Потребитель Kafka сообщений.
    Слушает топик 'new_order' и отправляет задачи в Celery.
    """
    kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")

    consumer = AIOKafkaConsumer(
        "new_order",
        bootstrap_servers=kafka_servers,
        group_id="order_consumer_group",
        auto_offset_reset="earliest",
    )

    try:
        logger.info(f"Подключение к Kafka: {kafka_servers}")
        await consumer.start()
        logger.info("Потребитель Kafka успешно запущен")

        async for msg in consumer:
            try:
                data = json.loads(msg.value)
                order_id = data.get("order_id")

                if not order_id:
                    logger.warning(f"Сообщение без order_id: {msg.value}")
                    continue

                logger.info(f"Получено сообщение для заказа: {order_id}")

                # Отправка задачи в Celery
                celery_app.send_task("app.tasks.process_order", args=[order_id])
                logger.info(f"Задача Celery отправлена для заказа {order_id}")

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при разборе JSON: {e}, сообщение: {msg.value}")
            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения: {e}")

    except Exception as e:
        logger.error(f"Ошибка потребителя Kafka: {e}")
        raise
    finally:
        await consumer.stop()
        logger.info("Потребитель Kafka остановлен")


if __name__ == "__main__":
    asyncio.run(consume())
