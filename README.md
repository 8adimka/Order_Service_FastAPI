# Сервис управления заказами (Microservices)

Микросервисная архитектура на FastAPI с PostgreSQL, Kafka (event-bus), Celery (background tasks), Redis (cache/broker).

## Архитектура

### Сервисы

1. **Auth Service** (Port 8001) - аутентификация и управление JWT токенами
2. **Orders Service** (Port 8000) - управление заказами, кеширование, взаимодействие с Kafka
3. **Consumer** - прослушивает Kafka очередь и отправляет задачи в Celery
4. **Celery Worker** - выполняет фоновые задачи обработки заказов

### Компоненты

- **PostgreSQL** - две независимые БД (auth и orders)
- **Redis** - кеширование заказов и broker для Celery
- **Kafka** - event-bus для публикации событий new_order
- **Celery** - асинхронная обработка задач
- **Docker Compose** - оркестрация всей инфраструктуры

## Требования

- Docker и Docker Compose
- Python 3.9+ (для локальной разработки)

## Установка и запуск

### 1. Клонируйте репозиторий

```bash
git clone <repo>
cd order_service_fastAPI
```

### 2. Создайте .env файл

```bash
cp .env.example .env
```

**ВАЖНО:** Отредактируйте `.env` и измените дефолтные пароли для production:

```env
# Очень важно для production!
POSTGRES_AUTH_PASSWORD=<generate-strong-password>
POSTGRES_ORDERS_PASSWORD=<generate-strong-password>

# Если используете Google OAuth2:
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8001/auth/callback/google
```

### 3. Запустите проект через Docker Compose

Docker Compose автоматически применит миграции при запуске:

```bash
docker compose up -d --build
```

**ВАЖНО:** Контейнеры будут инициализировать БД и применять миграции автоматически.

### 4. Проверить здоровье сервисов

```bash
# Проверить все сервисы
docker compose ps

# Проверить health endpoints
curl http://localhost:8001/health  # Auth Service
curl http://localhost:8000/health  # Orders Service
```

### 5. Просмотреть логи

```bash
# Все логи
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f auth
docker compose logs -f orders
docker compose logs -f celery_worker
docker compose logs -f order_consumer
```

### 6. Остановить проект

```bash
docker compose down  # Остановить контейнеры
docker compose down -v  # Остановить контейнеры и удалить volumes
```

## Swagger UI и документация

- **Auth Service Swagger**: <http://localhost:8001/docs>
- **Orders Service Swagger**: <http://localhost:8000/docs>

## API Эндпоинты

### Auth Service (Port 8001)

#### Регистрация пользователя

```bash
curl -X POST "http://localhost:8001/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'
```

**Ответ:**

```json
{
  "msg": "User created",
  "user_id": 1
}
```

#### Получение JWT токена (OAuth2 Password Flow)

```bash
curl -X POST "http://localhost:8001/auth/token/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=secure_password"
```

**Ответ:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Orders Service (Port 8000)

#### Создание заказа (требует авторизации)

```bash
curl -X POST "http://localhost:8000/orders/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"name": "Item 1", "price": 10.0, "quantity": 2},
      {"name": "Item 2", "price": 20.0, "quantity": 1}
    ],
    "total_price": 40.0
  }'
```

**Ответ:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "items": [...],
  "total_price": 40.0,
  "status": "PENDING",
  "created_at": "2026-02-16T10:30:00"
}
```

#### Получение заказа (из Redis кеша если доступен)

```bash
curl -X GET "http://localhost:8000/orders/550e8400-e29b-41d4-a716-446655440000/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Обновление статуса заказа

```bash
curl -X PATCH "http://localhost:8000/orders/550e8400-e29b-41d4-a716-446655440000/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "PAID"
  }'
```

#### Получение всех заказов пользователя

```bash
curl -X GET "http://localhost:8000/orders/user/1/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Мониторинг

### Логи сервисов

```bash
# Auth Service
docker compose logs -f auth

# Orders Service
docker compose logs -f orders

# Kafka Consumer
docker compose logs -f consumer

# Celery Worker
docker compose logs -f celery_worker

# Redis
docker compose logs -f redis

# Kafka
docker compose logs -f kafka
```

## Redis Архитектура

Redis используется с разделением на 3 логических БД:

| БД | Назначение | Компонент |
|----|-----------|-----------|
| **0** | Celery broker (очередь задач) + кеш заказов | Orders Service + Celery Worker |
| **1** | Celery результаты (результаты выполненных задач) | Celery Worker + клиенты |
| **2** | Rate limiter (счетчики запросов) | slowapi (защита API) |

Эта архитектура предотвращает конфликт данных между разными компонентами.

### Проверка Redis

```bash
docker compose exec redis redis-cli

# Проверить данные в каждой БД:
SELECT 0
KEYS *  # Celery задачи и кеш заказов

SELECT 1
KEYS *  # Результаты Celery

SELECT 2
KEYS *  # Rate limit счетчики
```

## Kafka Event Bus

При создании заказа:

1. Заказ сохраняется в БД
2. Публикуется событие `new_order` в Kafka топик
3. Consumer подписан на этот топик
4. Consumer получает сообщение и отправляет задачу в Celery

### Проверка Kafka

```bash
# Просмотр сообщений в топике new_order
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:29092 \
  --topic new_order \
  --from-beginning
```

## Celery Background Tasks

Consumer отправляет задачи в Celery Worker:

- **Задача:** `process_order(order_id)`
- **Действие:** имитирует обработку платежа (sleep 2 сек) + обновляет статус заказа на PAID в БД
- **Broker:** Redis (DB 0)
- **Result Backend:** Redis (DB 1)
- **Retries:** 3 попытки с exponential backoff

### Проверка Celery

```bash
docker compose logs -f celery_worker
```

Вы должны видеть логи вроде:

```
Starting to process order 550e8400-e29b-41d4-a716-446655440000
Order 550e8400-e29b-41d4-a716-446655440000 successfully updated to PAID status
```

## Redis Кеширование

При запросе заказа (`GET /orders/{order_id}/`):

1. Сначала проверяется Redis кеш (`key: order:{order_id}`)
2. Если найден - возвращается сразу (из DB 0)
3. Если нет - запрос идёт в БД и результат кешируется на **5 минут**
4. При обновлении заказа кеш обновляется

## Rate Limiting

API endpoint `/orders/*` имеет ограничение: **10 запросов в минуту per IP address**.

Счетчики хранятся в Redis DB 2 (slowapi).

При превышении лимита вернётся ответ:

```json
{
  "detail": "Rate limit exceeded"
}
```

- Result Backend: Redis

## Безопасность

✅ **Реализовано:**

- **JWT аутентификация (RS256 - асимметричный алгоритм)**
  - Auth Service подписывает токены приватным ключом (`private.pem`)
  - Orders Service проверяет токены публичным ключом (`public.pem`)
  - Только Auth Service может создавать корректные токены
  - Token lifespan: 30 минут (AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
  
- **OAuth2 Password Flow с CSRF защитой**
  - Google OAuth2 использует state parameter для защиты от CSRF атак
  - State генерируется при `google_login()`, проверяется при `google_callback()`
  - Используются secure httponly cookies для хранения state

- **Хеширование паролей (bcrypt)**
  - Пароли хешируются при регистрации и не хранятся в открытом виде
  - Проверка пароля при аутентификации через bcrypt verify

- **CORS ограничение**
  - Разрешены только запросы с localhost
  - Предотвращает кросс-доменные атаки

- **SQL injection защита**
  - Используется только SQLAlchemy ORM (параметризованные запросы)
  - Никогда не используется сырая SQL (raw SQL)

- **Rate limiting (slowapi)**
  - 10 запросов в минуту per IP address
  - Защищает API от DDoS и перебора паролей

- **Все чувствительные данные загружаются из .env**
  - Пароли БД, Redis, ключи API не в коде
  - .env файл в .gitignore

❌ **НЕ РЕАЛИЗОВАНО в demo:**

- **HTTPS/TLS** (используется HTTP локально для development)
  - Production: необходимо добавить SSL сертификаты
  
- **JWT refresh tokens** (используются долгоживущие токены)
  - Production: добавить refresh токены с механизмом ротации
  
- **Более строгая CORS политика**
  - Production: указать конкретные domains вместо localhost

## Структура проекта

```
order_service_fastAPI/
├── docker-compose.yml          # Оркестрация контейнеров
├── .env.example                # Пример конфигурации
├── README.md                   # Документация
└── services/
    ├── auth/                   # Auth Service
    │   ├── app/
    │   │   ├── main.py         # FastAPI приложение
    │   │   ├── config.py       # Настройки
    │   │   ├── models.py       # SQLAlchemy модели (User)
    │   │   ├── schemas.py      # Pydantic схемы
    │   │   ├── crud.py         # CRUD операции
    │   │   ├── database.py     # Подключение к БД
    │   │   ├── dependencies.py # OAuth2 зависимости
    │   │   ├── routers/
    │   │   │   └── auth.py     # API routes
    │   │   └── alembic/        # Миграции БД
    │   ├── requirements.txt
    │   └── Dockerfile
    │
    ├── orders/                 # Orders Service
    │   ├── app/
    │   │   ├── main.py         # FastAPI приложение
    │   │   ├── config.py       # Настройки
    │   │   ├── models.py       # SQLAlchemy модели (Order)
    │   │   ├── schemas.py      # Pydantic схемы
    │   │   ├── crud.py         # CRUD операции
    │   │   ├── database.py     # Подключение к БД
    │   │   ├── dependencies.py # OAuth2 валидация
    │   │   ├── cache.py        # Redis интеграция
    │   │   ├── kafka.py        # Kafka producer
    │   │   ├── limiter.py      # Rate limiting
    │   │   ├── tasks.py        # Celery задачи
    │   │   ├── routers/
    │   │   │   └── orders.py   # API routes
    │   │   └── alembic/        # Миграции БД
    │   ├── requirements.txt
    │   └── Dockerfile
    │
    └── consumer/               # Kafka Consumer -> Celery
        ├── consumer.py         # Потребитель Kafka
        ├── requirements.txt
        └── Dockerfile
```

## End-to-End Testing

### 1. Запустите весь проект

```bash
# Полная перезагрузка с очисткой данных
docker compose down -v
docker compose up -d --build

# Дождитесь инициализации (примерно 30 секунд)
docker compose ps
# Все сервисы должны быть в статусе "running"
```

### 2. Проверьте здоровье сервисов

```bash
# Auth Service
curl http://localhost:8001/health
# Ожидаемо: {"status": "ok"}

# Orders Service
curl http://localhost:8000/health
# Ожидаемо: {"status": "ok"}
```

### 3. Сценарий регистрации и получения токена

```bash
# 3a. Зарегистрируйте нового пользователя
curl -X POST "http://localhost:8001/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'

# Ожидаемо:
# {
#   "msg": "User created",
#   "user_id": 1
# }

# 3b. Получите JWT токен
RESPONSE=$(curl -s -X POST "http://localhost:8001/auth/token/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpassword123")

# Извлеките токен (на bash):
TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "Token: $TOKEN"

# Или вручную скопируйте access_token из ответа выше
```

### 4. Сценарий создания заказа

```bash
# Замените YOUR_TOKEN на реальный токен из шага 3b
curl -X POST "http://localhost:8000/orders/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"name": "Laptop", "price": 999.99, "quantity": 1},
      {"name": "Mouse", "price": 29.99, "quantity": 2}
    ],
    "total_price": 1059.97
  }'

# Ожидаемо:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "user_id": 1,
#   "items": [...],
#   "total_price": 1059.97,
#   "status": "PENDING",
#   "created_at": "2026-02-16T10:30:00Z"
# }

# Запомните ORDER_ID для следующих шагов
```

### 5. Проверьте Kafka событие

```bash
# Просмотрите сообщение в Kafka топике
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic new_order \
  --from-beginning \
  --max-messages 1

# Ожидаемо видеть JSON:
# {
#   "order_id": "550e8400-e29b-41d4-a716-446655440000",
#   "user_id": 1,
#   "timestamp": "2026-02-16T10:30:00Z"
# }
```

### 6. Проверьте Celery обработку

```bash
# Смотрите логи Celery Worker (в другом терминале)
docker compose logs -f celery_worker

# Ожидаемо видеть:
# [INFO] Starting to process order 550e8400-e29b-41d4-a716-446655440000
# [INFO] Order 550e8400-e29b-41d4-a716-446655440000 successfully updated to PAID status
```

### 7. Проверьте обновление статуса заказа

```bash
# Дождитесь 2-3 секунд, затем получите заказ
# Статус должен измениться с PENDING на PAID

curl -X GET "http://localhost:8000/orders/550e8400-e29b-41d4-a716-446655440000/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Ожидаемо:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "PAID",  <-- ИЗМЕНИЛСЯ!
#   ...
# }

# Примечание: Результат может быть из Redis кеша (быстро)
# или из БД если кеш истёк
```

### 8. Проверьте Redis кеш

```bash
# Подключитесь к Redis
docker compose exec redis redis-cli

# Проверьте все 3 БД
SELECT 0
KEYS *  # Должны быть ключи order:* и celery задачи
GET order:550e8400-e29b-41d4-a716-446655440000  # Должен быть кеш

SELECT 1
KEYS *  # Должны быть результаты Celery

SELECT 2
KEYS *  # Должны быть rate limit счетчики

exit
```

### 9. Проверьте Rate Limiting

```bash
# Сделайте 11 запросов подряд (лимит 10 в минуту)
for i in {1..11}; do
  curl -X GET "http://localhost:8000/orders/user/1/" \
    -H "Authorization: Bearer YOUR_TOKEN"
  echo "Request $i"
done

# Первые 10 должны вернуть 200 OK
# 11-й должен вернуть 429 Too Many Requests
```

### 10. Проверьте PostgreSQL миграции

```bash
# Auth Service миграции
docker compose exec auth alembic current
# Ожидаемо: 0001_create_users_table

# Orders Service миграции
docker compose exec orders alembic current
# Ожидаемо: 0001_create_orders_table
```

### 11. Просмотрите данные в БД

```bash
# Auth Database
docker compose exec postgres_auth psql -U authuser -d authdb -c "SELECT * FROM users;"

# Orders Database
docker compose exec postgres_orders psql -U ordersuser -d ordersdb -c "SELECT * FROM orders;"
```

## Полный сценарий в скрипте (bash)

```bash
#!/bin/bash

echo "=== Starting Full E2E Test ==="

# Restart
docker compose down -v
docker compose up -d --build
sleep 30

# 1. Register
echo "1. Registering user..."
REGISTER=$(curl -s -X POST "http://localhost:8001/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }')
echo $REGISTER

# 2. Get Token
echo "2. Getting JWT token..."
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8001/auth/token/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123")
TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "Token: $TOKEN"

# 3. Create Order
echo "3. Creating order..."
ORDER=$(curl -s -X POST "http://localhost:8000/orders/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [{"name": "Test Item", "price": 100.0, "quantity": 1}],
    "total_price": 100.0
  }')
ORDER_ID=$(echo $ORDER | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "Order ID: $ORDER_ID"

# 4. Wait for Celery processing
echo "4. Waiting for Celery to process order (3 seconds)..."
sleep 3

# 5. Check order status
echo "5. Checking order status..."
curl -s -X GET "http://localhost:8000/orders/$ORDER_ID/" \
  -H "Authorization: Bearer $TOKEN" | grep -o '"status":"[^"]*'

echo "=== E2E Test Complete ==="
```

## Troubleshooting

### Ошибка подключения к Kafka

```
Connection refused: localhost:9092
```

**Решение:** Убедитесь, что `KAFKA_BOOTSTRAP_SERVERS=kafka:29092` в .env

### PostgreSQL миграции не применяются

```bash
# Проверить статус миграций
docker compose exec auth alembic current

# Создать новую миграцию (если нужна)
docker compose exec auth alembic revision --autogenerate -m "migration_name"
```

### Redis кеш не работает

```bash
# Проверить Redis
docker compose exec redis redis-cli ping
# Должно вернуть: PONG
```

### Celery задачи не выполняются

```bash
# Проверить логи worker
docker compose logs celery_worker

# Проверить Redis для задач
docker compose exec redis redis-cli
KEYS *  # Должны быть задачи
```

## Полезные команды

```bash
# Перестройка контейнеров
docker compose down -v
docker compose up -d --build

# Очистка всех данных
docker compose down -v

# Логи всех сервисов в реальном времени
docker compose logs -f

# Вход в контейнер
docker compose exec orders bash
docker compose exec auth bash

# Проверка здоровья сервисов
docker compose ps
```

## Лицензия

MIT
