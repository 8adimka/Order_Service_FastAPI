# Сервис управления заказами (Microservices)

Микросервисная архитектура на FastAPI с PostgreSQL, Kafka (event-bus), Celery (tasks), Redis (cache/broker).

## Установка и запуск

1. Клонируйте репозиторий.
2. Скопируйте `.env.example` в `.env` и настройте (SECRET_KEY обязательно!).
3. Запустите: `docker compose up -d --build`
4. Миграции:
docker compose exec auth alembic upgrade head
docker compose exec orders alembic upgrade head

text
5. Swagger:

- Auth: <http://localhost:8001/docs>
- Orders: <http://localhost:8000/docs>

## Тестирование

**Register (Auth):**
curl -X POST "<http://localhost:8001/register/>"
-H "Content-Type: application/json"
-d '{"email": "<test@test.com>", "password": "password123"}'

text

**Token (Auth):**
curl -X POST "<http://localhost:8001/token/>"
-H "Content-Type: application/x-www-form-urlencoded"
-d "username=<test@test.com>&password=password123"

text
Получите access_token.

**Create Order (Orders):**
curl -X POST "<http://localhost:8000/orders/>"
-H "Authorization: Bearer YOUR_JWT_TOKEN"
-H "Content-Type: application/json"
-d '{
"items": [{"name": "Item1", "price": 10.0, "quantity": 2}],
"total_price": 20.0
}'

text

Проверьте логи: `docker compose logs consumer`, `docker compose logs celery_worker`

**Другие эндпоинты:** Swagger.

## Rate Limits

- /orders/*: 10/min per IP

## Архитектура

- Auth: /register, /token (JWT)
- Orders: CRUD orders (cache Redis, pub Kafka)
- Consumer: Kafka -> Celery task
- Worker: process_order (async heavy)
