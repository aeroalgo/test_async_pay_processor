# Payment Processor

Асинхронный микросервис для приёма платежей, гарантированной публикации событий через Outbox и асинхронной обработки через RabbitMQ.

## Коротко о сервисе

Что делает сервис:
- принимает платёж через HTTP API;
- сохраняет `payment` и `outbox` в одной транзакции;
- relay публикует событие `payments.new` в RabbitMQ;
- consumer обрабатывает платёж асинхронно;
- после обработки отправляет webhook;
- при ошибке webhook делает retry;
- при ошибке обработки сообщения RabbitMQ уходит в DLQ.

Основные свойства:
- авторизация по `X-API-Key`;
- идемпотентность по заголовку `Idempotency-Key`;
- статусы платежа: `pending`, `succeeded`, `failed`;
- retry webhook: 3 попытки;
- DLQ: `payments.new.dlq`.

## Стек

- FastAPI
- Pydantic v2
- SQLAlchemy 2.0 async
- PostgreSQL
- RabbitMQ
- FastStream
- Alembic
- Docker Compose

## Схема работы

```mermaid
graph TD
    Client[Клиент] -->|POST /api/v1/payments| API[FastAPI API]
    API -->|TX: payment + outbox| PG[(PostgreSQL)]
    API -->|relay pending events| RMQ[RabbitMQ exchange/queue]
    RMQ --> Consumer[FastStream Consumer]
    Consumer -->|update status| PG
    Consumer -->|POST webhook| Webhook[Webhook endpoint]
    RMQ -->|failed retries| DLQ[payments.new.dlq]
```

## Компоненты после запуска

После `docker-compose up -d` поднимаются:
- `postgres` — база данных `payments`;
- `rabbitmq` — брокер сообщений;
- `migrate` — одноразовый контейнер с `alembic upgrade head`;
- `api` — HTTP API на `http://localhost:8000`;
- `consumer` — асинхронный обработчик платежей.

Полезные адреса:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- RabbitMQ UI: [http://localhost:15672](http://localhost:15672)

RabbitMQ credentials:
- login: `guest`
- password: `guest`

## Полное развёртывание

### 1. Требования

Нужно, чтобы были установлены:
- Docker
- Docker Compose

### 2. Подготовка окружения

В корне проекта:

```bash
cp .env.example .env
```

Текущее содержимое `.env.example`:

```env
ENVIRONMENT=local
POSTGRES_URI=postgresql+asyncpg://payments:payments@localhost:5432/payments
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
API_KEY=dev-api-key-change-me
OUTBOX_POLL_INTERVAL_SEC=1
WEBHOOK_MAX_RETRIES=3
WEBHOOK_RETRY_BASE_DELAY_SEC=1
```

Если хотите, можно поменять `API_KEY`, но тогда используйте его во всех запросах ниже.

### 3. Запуск сервиса

Из корня проекта:

```bash
docker-compose up -d --build
```

Проверить состояние контейнеров:

```bash
docker-compose ps
```

Посмотреть логи:

```bash
docker-compose logs -f
```

Отдельно API:

```bash
docker-compose logs -f api
```

Отдельно consumer:

```bash
docker-compose logs -f consumer
```

### 4. Проверка готовности

Проверьте health endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

Проверьте защищённый endpoint:

```bash
curl http://localhost:8000/api/v1/health/protected \
  -H "X-API-Key: dev-api-key-change-me"
```

Ожидаемый ответ:

```json
{"authenticated":true}
```

## Как проверить работу после `docker-compose up -d`

Ниже минимальный сценарий smoke-проверки.

### Шаг 1. Подготовить переменные

```bash
export API_URL="http://localhost:8000"
export API_KEY="dev-api-key-change-me"
export IDEMPOTENCY_KEY="$(uuidgen)"
export HOOK_ID="$(uuidgen)"
```

### Шаг 2. Настроить тестовый webhook endpoint

В сервисе есть внутренний test hook API для проверки доставки webhook.

Создать endpoint, который сразу принимает webhook без ошибок:

```bash
curl -X PUT "$API_URL/api/v1/test-hooks/$HOOK_ID/config" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "failures_before_success": 0
  }'
```

Ожидаемый ответ: `200 OK`.

### Шаг 3. Создать платёж

```bash
curl -X POST "$API_URL/api/v1/payments" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d "{
    \"amount\": \"100.50\",
    \"currency\": \"RUB\",
    \"description\": \"Smoke payment\",
    \"metadata\": {\"order_id\": \"order-123\"},
    \"webhook_url\": \"$API_URL/api/v1/test-hooks/$HOOK_ID/deliver\"
  }"
```

Ожидаемый ответ:

```json
{
  "message": "Данные успешно добавлены",
  "meta": {},
  "data": {
    "payment_id": "uuid",
    "status": "pending",
    "created_at": "timestamp"
  }
}
```

Сохраните `payment_id` из ответа.

### Шаг 4. Проверить идемпотентность

Отправьте тот же запрос ещё раз с тем же `Idempotency-Key`.

```bash
curl -X POST "$API_URL/api/v1/payments" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d "{
    \"amount\": \"100.50\",
    \"currency\": \"RUB\",
    \"description\": \"Smoke payment\",
    \"metadata\": {\"order_id\": \"order-123\"},
    \"webhook_url\": \"$API_URL/api/v1/test-hooks/$HOOK_ID/deliver\"
  }"
```

Ожидаемое поведение:
- статус ответа снова `202`;
- `payment_id` должен быть тем же самым;
- новая запись платежа не создаётся.

### Шаг 5. Проверить финальный статус платежа

Consumer обрабатывает платёж асинхронно, поэтому подождите несколько секунд и выполните:

```bash
curl "$API_URL/api/v1/payments/<payment_id>" \
  -H "X-API-Key: $API_KEY"
```

Ожидаемое поведение:
- сначала статус может быть `pending`;
- затем должен стать `succeeded` или `failed`.

Пример ответа:

```json
{
  "message": "Данные успешно получены",
  "meta": {},
  "data": {
    "payment_id": "uuid",
    "amount": "100.50",
    "currency": "RUB",
    "description": "Smoke payment",
    "metadata": {
      "order_id": "order-123"
    },
    "status": "succeeded",
    "idempotency_key": "uuid",
    "webhook_url": "http://localhost:8000/api/v1/test-hooks/uuid/deliver",
    "created_at": "timestamp",
    "processed_at": "timestamp",
    "failure_reason": null
  }
}
```

### Шаг 6. Проверить, что webhook действительно пришёл

```bash
curl "$API_URL/api/v1/test-hooks/$HOOK_ID" \
  -H "X-API-Key: $API_KEY"
```

Ожидаемое поведение:
- `attempts` должно быть `1`;
- `successful_deliveries` должно быть `1`;
- в `last_payload` должен быть результат обработки платежа.

Пример ответа:

```json
{
  "message": "Данные успешно получены",
  "meta": {},
  "data": {
    "failures_before_success": 0,
    "attempts": 1,
    "successful_deliveries": 1,
    "last_payload": {
      "payment_id": "uuid",
      "status": "succeeded",
      "amount": "100.50",
      "currency": "RUB",
      "processed_at": "timestamp"
    }
  }
}
```

## Как проверить retry webhook

Если хотите увидеть retry вживую:

### 1. Настройте test hook на две ошибки перед успехом

```bash
export RETRY_HOOK_ID="$(uuidgen)"

curl -X PUT "$API_URL/api/v1/test-hooks/$RETRY_HOOK_ID/config" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "failures_before_success": 2
  }'
```

### 2. Создайте платёж с webhook на этот endpoint

```bash
curl -X POST "$API_URL/api/v1/payments" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d "{
    \"amount\": \"250.00\",
    \"currency\": \"USD\",
    \"description\": \"Retry webhook test\",
    \"metadata\": {\"order_id\": \"retry-1\"},
    \"webhook_url\": \"$API_URL/api/v1/test-hooks/$RETRY_HOOK_ID/deliver\"
  }"
```

### 3. Через несколько секунд проверьте hook state

```bash
curl "$API_URL/api/v1/test-hooks/$RETRY_HOOK_ID" \
  -H "X-API-Key: $API_KEY"
```

Ожидаемое поведение:
- `attempts` будет `3`;
- `successful_deliveries` будет `1`.

## Как проверить отказ webhook после всех retry

```bash
export FAIL_HOOK_ID="$(uuidgen)"

curl -X PUT "$API_URL/api/v1/test-hooks/$FAIL_HOOK_ID/config" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "failures_before_success": 10
  }'
```

Потом создайте платёж с webhook:

```bash
curl -X POST "$API_URL/api/v1/payments" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d "{
    \"amount\": \"300.00\",
    \"currency\": \"EUR\",
    \"description\": \"Permanent webhook failure\",
    \"metadata\": {\"order_id\": \"fail-1\"},
    \"webhook_url\": \"$API_URL/api/v1/test-hooks/$FAIL_HOOK_ID/deliver\"
  }"
```

Проверьте состояние hook:

```bash
curl "$API_URL/api/v1/test-hooks/$FAIL_HOOK_ID" \
  -H "X-API-Key: $API_KEY"
```

Ожидаемое поведение:
- `attempts` будет `3`;
- `successful_deliveries` будет `0`;
- сам платёж при этом всё равно должен получить финальный статус `succeeded` или `failed`.

## API endpoints

### Public API

- `GET /api/v1/health`
- `GET /api/v1/health/protected`
- `POST /api/v1/payments`
- `GET /api/v1/payments/{payment_id}`

### Test hook API

- `PUT /api/v1/test-hooks/{hook_id}/config`
- `GET /api/v1/test-hooks/{hook_id}`
- `POST /api/v1/test-hooks/{hook_id}/deliver`

`test-hooks` нужны для проверки webhook delivery и retry, они не являются бизнесовым API для внешних клиентов.