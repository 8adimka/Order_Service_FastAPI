import json

from aiokafka import AIOKafkaProducer

from .config import settings

producer = AIOKafkaProducer(
    bootstrap_servers=settings.kafka_bootstrap_servers,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)


async def send_new_order(order_id: str):
    await producer.send_and_wait("new_order", {"order_id": order_id})
