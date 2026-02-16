import asyncio
import json
import os

from aiokafka import AIOKafkaConsumer
from celery import Celery

celery_app = Celery("consumer", broker=os.getenv("CELERY_BROKER_URL"))


async def consume():
    consumer = AIOKafkaConsumer(
        "new_order",
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
        group_id="order_consumer_group",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value)
            order_id = data["order_id"]
            celery_app.send_task("tasks.process_order", args=[order_id])
            print(f"Sent Celery task for order {order_id}")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(consume())
