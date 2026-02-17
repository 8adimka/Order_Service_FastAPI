import json
from uuid import UUID

from aiokafka import AIOKafkaProducer

from .config import settings


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


producer = AIOKafkaProducer(
    bootstrap_servers=settings.kafka_bootstrap_servers,
    value_serializer=lambda v: json.dumps(v, cls=CustomEncoder).encode("utf-8"),
)


async def send_new_order(order_id):
    # Convert UUID to string if needed
    order_id_str = str(order_id) if isinstance(order_id, UUID) else order_id
    await producer.send_and_wait("new_order", {"order_id": order_id_str})
