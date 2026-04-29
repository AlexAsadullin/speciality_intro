# Trading Data Parsing

Сервис сбора макроэкономических и рыночных данных для обучения торговых ИИ-агентов.
Источники: ЦБ РФ, MOEX, Росстат (fedstat.ru), Минфин (opendata + minfin.gov.ru).

## Стек

| Слой | Технология |
|---|---|
| Web framework | FastAPI + Uvicorn (async) |
| База данных | PostgreSQL + asyncpg + SQLAlchemy 2 (async ORM) |
| Миграции | Alembic |
| Хранилище файлов | MinIO (S3-совместимый) через aioboto3 |
| Auth | JWT (python-jose), bcrypt |
| HTTP-клиент | httpx (async) |
| Парсинг | lxml, BeautifulSoup4, cloudscraper |
| Загрузчики данных | cbrapi, moexalgo |
| Python | 3.12+ |

## Требования

- Python 3.12+
- PostgreSQL 15+
- MinIO (или любой S3-совместимый эндпоинт)
- MOEX AlgoPack токен (только для `/moex/orderbook`, `/moex/tradestats`, `/moex/orderstats`)

## Сборка и запуск

### 1. Клонировать и настроить окружение

```bash
git clone <repo>
cd trading_data_parsing

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настроить переменные окружения

Создать `.env` в корне проекта:

```env
DATABASE_URL=postgresql+asyncpg://trading_user:password@localhost:5432/trading_data
JWT_SECRET_KEY=your-secret-key-min-32-chars
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=trading-data
MINIO_USE_SSL=false
DATA_ROOT=/tmp/trading_data
MOEX_ALGOPACK_TOKEN=your-token   # опционально
```

### 3. Создать БД и применить миграции

```bash
createdb -U postgres trading_data
psql -U postgres -c "CREATE USER trading_user WITH PASSWORD 'password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE trading_data TO trading_user;"

alembic upgrade head
```

### 4. Запустить MinIO (локально через Docker)

```bash
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

### 5. Запустить приложение

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI: http://localhost:8000/docs

### Запуск тестов

Тесты используют SQLite in-memory и не требуют PostgreSQL/MinIO:

```bash
pytest tests/ -v
```

## Структура проекта

```
.
├── config.py               # все константы: пути, URL, тикеры, дефолты
├── app/
│   ├── main.py             # FastAPI app, обработчики ошибок, lifespan
│   ├── settings.py         # Settings (pydantic-settings, .env)
│   ├── auth/               # регистрация, login, JWT, refresh, logout
│   ├── routers/            # cbr.py, moex.py, rosstat.py, minfin.py
│   ├── models/             # ORM-модели: User, UserRequest
│   ├── schemas.py          # Pydantic-схемы ответов
│   ├── services/
│   │   ├── loader_runner.py   # оркестратор: вызов загрузчика → MinIO → лог в БД
│   │   └── minio_client.py    # async S3 через aioboto3
│   ├── crud/               # user_request CRUD
│   ├── db/                 # session, base
│   └── exceptions.py       # LoaderError, MinIOError
├── loader/
│   ├── helpers.py          # RunReport, ensure_dir, save_csv, parse_date
│   ├── cbr/cbr.py          # ЦБ РФ через cbrapi (async + asyncio.to_thread)
│   ├── moex/algopack.py    # MOEX через moexalgo (async + asyncio.to_thread)
│   ├── rosstat/parsers.py  # fedstat.ru SDMX + HTML fallback (httpx async)
│   └── minfin/parsers.py   # OpenData CSV + cloudscraper doc-cards
├── migrations/             # Alembic-миграции
├── tests/                  # pytest + pytest-asyncio
└── data/                   # scratch-директория для CSV перед загрузкой в MinIO
```

## API — эндпоинты

Все эндпоинты (кроме `/auth/*`) требуют заголовка:
```
Authorization: Bearer <access_token>
```

### Auth

| Метод | Путь | Описание |
|---|---|---|
| POST | `/auth/register` | Регистрация пользователя |
| POST | `/auth/login` | Получение access + refresh токенов |
| POST | `/auth/refresh` | Обновление токенов по refresh token |
| POST | `/auth/logout` | Инвалидация refresh token |

### CBR (ЦБ РФ)

Параметры: `first_date` и `last_date` в формате `YYYY-MM-DD`.

| GET | Описание |
|---|---|
| `/cbr/key_rate` | Ключевая ставка ЦБ РФ |
| `/cbr/refinancing_rate` | Ставка рефинансирования (с 2016 = ключевая) |
| `/cbr/ruonia` | Индекс RUONIA |
| `/cbr/currency_rates` | Курсы валют (USD, EUR, CNY) |
| `/cbr/reserves` | Международные резервы (ежемесячно) |
| `/cbr/metals_prices` | Учётные цены на драгметаллы |
| `/cbr/ibor` | Ставки IBOR |
| `/cbr/roisfix` | Ставки ROISFIX |

### MOEX

Параметры: `ticker` (обязательный), `first_date`, `last_date`.

| GET | Дополнительные параметры | Описание |
|---|---|---|
| `/moex/shares` | `period` (ONE_MINUTE/TEN_MINUTES/ONE_HOUR/ONE_DAY/ONE_WEEK/ONE_MONTH) | Свечи акций |
| `/moex/orderbook` | — | Статистика стакана (obstats) *¹* |
| `/moex/tradestats` | — | Торговая статистика *¹* |
| `/moex/orderstats` | — | Статистика заявок *¹* |
| `/moex/indices` | — | Дневные свечи индексов (IMOEX и др.) |
| `/moex/ofz_curve` | — | Индекс кривой ОФЗ (RGBI/RGBITR) |
| `/moex/derivatives` | — | Дневные свечи фьючерсов |

*¹ Требует платный токен MOEX AlgoPack.*

### Rosstat

| GET | Описание |
|---|---|
| `/rosstat/cpi` | Недельный ИПЦ (fedstat id=31074) |
| `/rosstat/ipp` | Индекс цен производителей (fedstat id=40557) |

### Minfin

| GET | Описание |
|---|---|
| `/minfin/budget` | Исполнение федерального бюджета (OpenData CSV) |
| `/minfin/fnb` | Объём ФНБ (OpenData CSV) |
| `/minfin/ofz_auctions` | Карточки документов по аукционам ОФЗ |
| `/minfin/state_support` | Карточки документов по господдержке бюджета |

### Формат успешного ответа (200)

```json
{
  "rows_downloaded": 1234,
  "files": ["cbr/key_rate/key_rate_2024-01-01_2024-06-01.csv"]
}
```

## Коды ошибок

| HTTP | type | Причина |
|---|---|---|
| 200 | — | Успех |
| 201 | — | Пользователь создан (`/auth/register`) |
| 204 | — | Logout выполнен |
| 400 | — | Некорректный запрос |
| 401 | — | Токен отсутствует, истёк или недействителен |
| 403 | — | Нет доступа к ресурсу |
| 409 | — | Username или email уже зарегистрирован |
| 422 | `validation_error` | Ошибка валидации параметров (неверный формат даты, `first_date > last_date`) |
| 502 | `loader_error` | Источник данных вернул 0 строк или недоступен; upstream 403 у MOEX (нет AlgoPack подписки) |
| 503 | `storage_error` | MinIO недоступен или ошибка при загрузке файла |
| 500 | `internal_error` | Непредвиденная ошибка сервера |

Тело ошибки:

```json
{
  "detail": "cbr/key_rate returned 0 rows — upstream may be unavailable",
  "type": "loader_error"
}
```

## Схема базы данных

### Таблица `users`

| Колонка | Тип | Описание |
|---|---|---|
| `id` | UUID PK | Генерируется автоматически |
| `username` | VARCHAR(64) UNIQUE | Логин |
| `email` | VARCHAR(256) UNIQUE | Email |
| `hashed_password` | VARCHAR(256) | bcrypt-хэш |
| `is_active` | BOOLEAN | Флаг активности (default: true) |
| `created_at` | TIMESTAMPTZ | Время регистрации |
| `refresh_token` | VARCHAR(512) | Текущий refresh token (nullable) |

### Таблица `user_requests`

| Колонка | Тип | Описание |
|---|---|---|
| `id` | UUID PK | Генерируется автоматически |
| `user_id` | UUID FK → users.id | Владелец запроса (CASCADE DELETE) |
| `requested_at` | TIMESTAMPTZ | Время запроса |
| `source` | VARCHAR(32) | Источник: `cbr`, `moex`, `rosstat`, `minfin` |
| `endpoint` | VARCHAR(64) | Эндпоинт: `key_rate`, `shares`, `cpi`, … |
| `rows_downloaded` | INTEGER | Количество скачанных строк |
| `parameters` | JSONB | Параметры запроса (даты, тикер и т.д.) |

## Хранилище файлов (MinIO)

Файлы хранятся в бакете `trading-data` (настраивается через `MINIO_BUCKET`).

Путь объекта: `{source}/{endpoint}/{filename}.csv`

Примеры:
```
cbr/key_rate/key_rate_2024-01-01_2024-06-01.csv
moex/shares/candles_one_day_SBER_2024-01-01_2024-06-01.csv
rosstat/cpi/cpi.csv
minfin/budget/budget.csv
```

## Загрузчики — запуск напрямую

Каждый загрузчик можно запустить как самостоятельный скрипт:

```bash
python loader/cbr/cbr.py
python loader/moex/algopack.py
python loader/rosstat/parsers.py
python loader/minfin/parsers.py
```

Результат сохраняется в `data/` локально (без MinIO).
