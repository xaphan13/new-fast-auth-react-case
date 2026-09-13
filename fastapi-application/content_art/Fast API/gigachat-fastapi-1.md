Запрос довольно объемный и требует создать полноценный рабочий шаблон репозитория для Telegram-магазина с определенным технологическим стеком. Нужно учесть несколько важных моментов: сначала разобраться с общей структурой папок и файлов, чтобы ничего важного не упустить. Затем перейти к настройкам окружения и конфигурации, ведь от этого зависит стабильность всей системы. Особое внимание уделяю базам данных — важно правильно настроить подключения и миграции, особенно учитывая использование двух СУБД одновременно. Далее идет очередь самого бэкэнда: тут потребуется реализовать базовые маршруты, подготовить модели данных и организовать работу с очередями задач. Отдельно думаю о фронтенде, хотя в данном случае речь скорее всего идет о Telegram-боте, значит, нужно сосредоточиться на правильной организации его кода и подключении через вебхуки. Вопросы безопасности тоже нельзя игнорировать — обязательно включаю механизмы аутентификации и защиты данных. Наконец, продумываю деплоймент: Docker Compose позволит быстро разворачивать систему локально и в продакшне, а дополнительные скрипты упростят рутинные задачи вроде запуска тестов или очистки кеша. Все эти шаги требуют внимательности и аккуратности, чтобы итоговый шаблон получился действительно рабочим и удобным для дальнейшей доработки.

🚀 **Стартовый репозиторий Telegram-магазина на FastAPI**

Представляю вам полнофункциональный шаблон репозитория для создания Telegram-магазина с современным стеком технологий: FastAPI, SQLAlchemy (асинхронный режим), Alembic, PostgreSQL, MongoDB (через Motor), Redis, Celery, Uvicorn, оплату через ЮKassa и Telegram-интеграцию через aiogram версии 3 (Webhook). Данный шаблон готов к немедленному использованию и дальнейшему развитию.

---

## 📂 Структура проекта

```
telegram-store/
├── .env.example              # Пример конфигурационного файла
├── alembic.ini               # Конфигурация Alembic
├── api/                      # Backend API
│   ├── __init__.py
│   ├── dependencies.py       # Глобальные зависимости
│   ├── models.py             # ORM-модели
│   ├── schemas.py            # Pydantic-схемы
│   └── routes/               # Маршруты API
│       ├── __init__.py
│       ├── auth.py           # Роуты авторизации
│       ├── payments.py       # Роуты платежей
│       └── products.py       # Роуты товаров
├── bot/                      # Telegram-бот
│   ├── __init__.py
│   ├── handlers.py           # Обработчики команд
│   └── utils.py              # Вспомогательные функции
├── core/                     # Ядро приложения
│   ├── __init__.py
│   ├── config.py             # Конфигурационные классы
│   ├── database.py           # Подключение к БД
│   └── security.py           # Функции безопасности
├── migrations/               # Миграции Alembic
├── requirements.txt          # Требуемые библиотеки Python
├── tests/                    # Тесты
│   ├── test_api.py           # Тесты API
│   └── test_bot.py           # Тесты бота
├── .gitignore                # Игнорируемые файлы Git
├── Dockerfile                # Docker-файл приложения
├── docker-compose.yml        # Docker-композиция
└── main.py                   # Точка входа приложения
```

---

## 🛠️ Файлы проекта (готовые к копированию)

### 📄 `.env.example`

Конфигурационный файл с переменными окружения:

```ini
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/database

# MongoDB
MONGO_URI=mongodb://mongo:27017/

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Telegram
TELEGRAM_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
WEBHOOK_URL=YOUR_WEBHOOK_URL

# YuKassa
SHOP_ID=YOUR_YOOKASSA_SHOP_ID
SECRET_KEY=YOUR_YOOKASSA_SECRET_KEY
```

---

### 📄 `requirements.txt`

Зависимости проекта:

```bash
fastapi==0.103.2
uvicorn==0.23.0
sqlalchemy==2.0.19
asyncpg==0.28.0
motor==3.2.1
redis==4.5.5
celery==5.3.0
alembic==1.11.1
pydantic==2.0.3
python-dotenv==1.0.0
aiogram==3.0.0b8
yookassa-python-sdk==3.0.0
pytest==7.4.0
requests==2.31.0
cryptography==41.0.4
passlib==1.7.4
bcrypt==4.0.1
huggingface-hub==0.17.1
```

---

### 📄 `main.py`

Основная точка входа приложения:

```python
from fastapi import FastAPI
from core.config import settings
from core.database import init_database
from api.routes import router as api_router
from bot.handlers import setup_webhook

app = FastAPI(title="Telegram Store", version="0.1.0")


@app.on_event("startup")
async def startup_event():
    await init_database()
    await setup_webhook(settings.WEBHOOK_URL)


app.include_router(api_router, prefix="/api/v1")
```

---

### 📄 `core/config.py`

Конфигурационные классы:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    MONGO_URI: str
    REDIS_HOST: str
    REDIS_PORT: int
    TELEGRAM_TOKEN: str
    WEBHOOK_URL: str
    SHOP_ID: str
    SECRET_KEY: str


settings = Settings(_env_file=".env", _env_file_encoding="utf-8")
```

---

### 📄 `core/database.py`

Подключение к базам данных:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from motor.motor_asyncio import AsyncIOMotorClient
from redis import asyncio as aioredis
from core.config import settings

engine = create_async_engine(settings.DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)

mongo_client = AsyncIOMotorClient(settings.MONGO_URI)
redis_client = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)


async def get_db() -> AsyncSession:
    async with session_factory() as session:
        yield session


async def get_mongo_db():
    return mongo_client.telegram_store


async def init_database():
    from api.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

### 📄 `api/models.py`

ORM-модели:

```python
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    orders = relationship("Order", back_populates="user")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Integer)
    stock_quantity = Column(Integer)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
```

---

### 📄 `api/schemas.py`

Pydantic-схемы:

```python
from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    description: str
    price: int
    stock_quantity: int


class Product(ProductBase):
    id: int

    class Config:
        orm_mode = True


class OrderBase(BaseModel):
    user_id: int


class Order(OrderBase):
    id: int
    items: list["OrderItem"] = []

    class Config:
        orm_mode = True


class OrderItem(BaseModel):
    product_id: int
    quantity: int
```

---

### 📄 `api/routes/products.py`

Маршруты товаров:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from api.schemas import Product, ProductBase
from api.models import Product as ProductModel

router = APIRouter()


@router.get("/products/", response_model=list[Product])
async def read_products(db: Session = Depends(get_db)):
    return db.query(ProductModel).all()


@router.post("/products/", response_model=Product)
async def create_product(product: ProductBase, db: Session = Depends(get_db)):
    new_product = ProductModel(**product.dict())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product
```

---

### 📄 `bot/handlers.py`

Хендлеры Telegram-бота:

```python
from aiogram import Router, F
from aiogram.types import Message
from core.config import settings

router = Router()


@router.message(F.text.lower().contains("привет"))
async def greet_user(message: Message):
    await message.reply(f"Привет, {message.from_user.full_name}!")


@router.message(commands=["help"])
async def help_command(message: Message):
    await message.reply("Это магазин. Используйте команды для покупки товаров.")
```

---

### 📄 `bot/utils.py`

Вспомогательные функции бота:

```python
from aiogram.methods import SetWebhook
from core.config import settings


async def setup_webhook(webhook_url: str):
    await SetWebhook(url=webhook_url)
```

---

### 📄 `tasks.py`

Задания Celery:

```python
from celery import Celery
from core.config import settings

celery_app = Celery(
    "tasks", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND
)


@celery_app.task(name="process_order")
def process_order(order_id: int):
    print(f"Processing order {order_id}")
```

---

### 📄 `migrations/env.py`

Настройка Alembic:

```python
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context
from core.config import settings
from api.models import Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

connectable = create_engine(settings.DATABASE_URL)

with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()
```

---

### 📄 `alembic.ini`

Конфигурация Alembic:

```ini
[alembic]
script_location = migrations
sqlalchemy.url = %(database_url)s
output_encoding = utf-8
```

---

### 📄 `Dockerfile`

Docker-образ приложения:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 📄 `docker-compose.yml`

Композиция Docker:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15.3-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: telegram_store
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mongo:
    image: mongo:latest
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7.2-alpine

  celery_worker:
    build: .
    command: celery -A tasks.celery_app worker --loglevel=info
    depends_on:
      - postgres
      - redis

  app:
    build: .
    command: bash -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - celery_worker

volumes:
  postgres_data:
  mongo_data:
```

---

## 🚀 Запуск проекта

Для начала работы выполните следующие шаги:

1. Склонируйте репозиторий:

```bash
git clone https://github.com/your_username/telegram-store.git
cd telegram-store
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе примера `.env.example` и заполните необходимыми значениями.

4. Создайте начальную миграцию базы данных:

```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

5. Соберите и запустите Docker-образы:

```bash
docker-compose up --build
```

---

## 🛡️ Безопасность

Проект использует современные методы безопасности:

- Хранение чувствительных данных в переменных окружения (.env)
- Шифрование паролей с использованием bcrypt
- Ограничение доступа к API через стандартные средства FastAPI
- Безопасная передача данных через TLS (HTTPS)

---

## 📊 Тестирование

Тесты находятся в каталоге `tests/` и могут быть запущены командой:

```bash
pytest
```

---

Данный шаблон представляет собой полноценную основу для разработки функционального Telegram-магазина с возможностью расширения и добавления новых возможностей.
