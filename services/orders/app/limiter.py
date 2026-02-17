from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings

# Используем отдельную Redis БД (DB 2) для rate limiter,
# чтобы избежать конфликта с Celery (DB 0) и результатами Celery (DB 1)
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_limiter_url)
