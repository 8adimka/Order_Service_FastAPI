import json
from datetime import datetime
from enum import Enum
from uuid import UUID

import redis

from .config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def get_cache(key: str):
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None


def set_cache(key: str, value: dict, ttl: int = 300):
    redis_client.setex(key, ttl, json.dumps(value, cls=CustomJSONEncoder))


def delete_cache(key: str):
    redis_client.delete(key)
