# Сервис управления заказами

Микросервисная архитектура на FastAPI с PostgreSQL, Kafka (event-bus), Celery (background tasks), Redis (cache/broker).

## Архитектура

### Сервисы

1. **Auth Service** (Port 8001) - аутентификация и управление JWT токенами (дополнительно добавил Google OAuth2)

- **JWT RS256**:

  - **Auth Service** имеет **приватный ключ** (`private.pem`) для **подписи** JWT токенов
  - **Orders Service** имеет **публичный ключ** (`public.pem`) для **проверки** JWT токенов
  - Алгоритм: `RS256` (асимметричная криптография)

1. **Orders Service** (Port 8000) - управление заказами, кеширование, взаимодействие с Kafka
2. **Consumer** - прослушивает Kafka очередь и отправляет задачи в Celery через Redis (как broker)
3. **Celery Worker** - выполняет фоновые задачи обработки заказов

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

### 3. Запустите проект через Docker Compose

Для удобства тестирования Docker Compose автоматически применит миграции при запуске:

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
  "id": "YOUR_ORDER_ID",
  "user_id": 1,
  "items": [...],
  "total_price": 40.0,
  "status": "PENDING",
  "created_at": "2026-02-16T10:30:00"
}
```

#### Получение заказа (из Redis кеша если доступен)

```bash
curl -X GET "http://localhost:8000/orders/YOUR_ORDER_ID/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Обновление статуса заказа

```bash
curl -X PATCH "http://localhost:8000/orders/YOUR_ORDER_ID/" \
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

## Безопасность

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
