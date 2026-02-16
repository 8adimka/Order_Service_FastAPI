import json

import redis

from .config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def get_cache(key: str):
    data = redis_client.get(key)
    return json.loads(data) if data else None


def set_cache(key: str, value: dict, ttl: int = 300):
    redis_client.setex(key, ttl, json.dumps(value))


def delete_cache(key: str):
    redis_client.delete(key)
