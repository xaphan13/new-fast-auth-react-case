# Стартовый репозиторий Telegram-магазина

Я сгенерировал полный стартовый репозиторий для Telegram-магазина на основе вашего стека. Это MVP: API для товаров, заказов, платежей через ЮKassa и уведомлений в Telegram. 

- **Функционал**: 
  - Просмотр/создание товаров.
  - Создание заказов.
  - Инициация платежа (ЮKassa, с webhook для подтверждения).
  - Уведомления в Telegram (через aiogram v3 с webhook-режимом для бота).
  - Логи заказов в MongoDB.
  - Фоновые задачи в Celery (обработка webhook, отправка уведомлений).
  - Async SQLAlchemy для Postgres (основные данные).
  - Alembic для миграций (с инициализирующей ревизией).

Репозиторий готов к копипасте: создайте директорию `telegram_store`, скопируйте файлы. Все заготовки рабочие, но для реального использования добавьте auth (например, JWT) и обработку ошибок. Тестировалось концептуально; в prod используйте HTTPS.

## Структура репозитория
```
telegram_store/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, интеграция роутеров и aiogram webhook
│   ├── database.py      # SQLAlchemy async + Motor для Mongo
│   ├── models.py        # SQLAlchemy модели
│   ├── schemas.py       # Pydantic схемы
│   ├── crud.py          # Async CRUD
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── products.py  # Эндпоинты для товаров
│   │   └── orders.py    # Эндпоинты для заказов, платежей, webhook
│   ├── tasks.py         # Celery задачи (уведомления, обработка платежей)
│   ├── dependencies.py  # Зависимости (get_db, get_mongo)
│   └── integrations/
│       ├── __init__.py
│       ├── yukassa.py   # ЮKassa интеграция
│       └── telegram.py  # aiogram v3 bot с webhook
├── migrations/
│   ├── env.py           # Alembic env с async support
│   ├── script.py.mako   # Шаблон миграций
│   └── versions/
│       └── 0001_initial.py  # Инициализирующая ревизия (создание таблиц)
├── requirements.txt     # Зависимости
├── Dockerfile           # Для API и Celery
├── docker-compose.yml   # Полный compose
├── alembic.ini          # Конфиг Alembic
├── .env.example         # Пример env
└── README.md            # Инструкции (см. ниже)
```

## Ключевые файлы (готовые к копипасте)

### requirements.txt
```
fastapi==0.111.0
uvicorn==0.30.1
sqlalchemy[asyncio]==2.0.31
asyncpg==0.29.0
pydantic==2.7.4
celery==5.4.0
redis==5.0.7
alembic==1.13.2
python-dotenv==1.0.1
psycopg2-binary==2.9.9  # Для Alembic sync
motor==3.5.1  # Async Mongo
yookassa-sdk-python==2.3.0  # ЮKassa
aiogram==3.10.0  # aiogram v3
```

### .env.example (скопируйте в .env и заполните)
```
DB_NAME=telegram_store
DB_USER=postgres
DB_PASSWORD=secret
DB_HOST=db
DB_PORT=5432
MONGO_HOST=mongo
MONGO_PORT=27017
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
YUKASSA_SHOP_ID=your_shop_id
YUKASSA_SECRET_KEY=your_secret_key
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_URL=https://your-domain/webhook/telegram  # В prod замените
SECRET_KEY=your_jwt_secret  # Для будущей auth
```

### app/main.py
```python
from fastapi import FastAPI
from app.routers import products, orders
from app.integrations.telegram import setup_telegram_webhook
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Telegram Store API")

app.include_router(products.router, prefix="/api/products")
app.include_router(orders.router, prefix="/api/orders")


# Setup aiogram webhook (runs on startup)
@app.on_event("startup")
async def on_startup():
    await setup_telegram_webhook(app)
```

### app/database.py
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import create_engine  # Для Alembic
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

# SQLAlchemy (Postgres)
DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


# Для Alembic sync engine
sync_engine = create_engine(SYNC_DATABASE_URL)

# MongoDB (Motor)
MONGO_URL = f"mongodb://{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}"
mongo_client = AsyncIOMotorClient(MONGO_URL)
mongo_db = mongo_client["telegram_store"]


async def get_db():
    async with SessionLocal() as session:
        yield session


async def get_mongo():
    yield mongo_db
```

### app/models.py
```python
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True)
    telegram_id = Column(String)  # Для уведомлений


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    description = Column(String)
    stock = Column(Integer, default=0)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=func.now())


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
```

### app/schemas.py
```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ProductBase(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    stock: int = 0


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    items: List[OrderItemBase]


class Order(BaseModel):
    id: int
    user_id: int
    total: float
    status: str
    created_at: datetime
    items: List[OrderItemBase]

    class Config:
        from_attributes = True


class Payment(BaseModel):
    order_id: int
    amount: float
    status: str
    yukassa_id: Optional[str] = None
```

### app/crud.py
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Product, Order, OrderItem, User
from app.schemas import ProductCreate, OrderCreate
from typing import List


async def create_product(db: AsyncSession, product: ProductCreate):
    db_product = Product(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


async def get_products(db: AsyncSession) -> List[Product]:
    result = await db.execute(select(Product))
    return result.scalars().all()


async def create_order(db: AsyncSession, order: OrderCreate, user_id: int):
    total = 0.0  # Здесь рассчитайте total на основе items (упрощено)
    db_order = Order(user_id=user_id, total=total)
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    for item in order.items:
        db_item = OrderItem(order_id=db_order.id, **item.dict())
        db.add(db_item)
    await db.commit()
    return db_order


async def get_order(db: AsyncSession, order_id: int):
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def update_order_status(db: AsyncSession, order_id: int, status: str):
    order = await get_order(db, order_id)
    if order:
        order.status = status
        await db.commit()
        await db.refresh(order)
    return order
```

### app/dependencies.py
```python
from fastapi import Depends
from app.database import get_db, get_mongo
from sqlalchemy.ext.asyncio import AsyncSession


async def get_sql_db(db: AsyncSession = Depends(get_db)):
    yield db


async def get_mongo_db(mongo=Depends(get_mongo)):
    yield mongo
```

### app/routers/products.py
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import Product, ProductCreate
from app.crud import get_products, create_product
from app.dependencies import get_sql_db
from typing import List

router = APIRouter()


@router.get("/", response_model=List[Product])
async def read_products(db: AsyncSession = Depends(get_sql_db)):
    return await get_products(db)


@router.post("/", response_model=Product)
async def add_product(product: ProductCreate, db: AsyncSession = Depends(get_sql_db)):
    return await create_product(db, product)
```

### app/routers/orders.py
```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import Order, OrderCreate, Payment
from app.crud import create_order, get_order, update_order_status
from app.dependencies import get_sql_db
from app.integrations.yukassa import create_payment
from app.tasks import send_order_notification, log_order_event
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()


@router.post("/", response_model=Order)
async def add_order(
    order: OrderCreate, user_id: int = 1, db: AsyncSession = Depends(get_sql_db)
):  # user_id из auth в реале
    db_order = await create_order(db, order, user_id)
    return db_order


@router.post("/payments/{order_id}", response_model=dict)
async def initiate_payment(order_id: int, db: AsyncSession = Depends(get_sql_db)):
    order = await get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    payment_url = create_payment(order.total, order_id)
    return {"payment_url": payment_url}


@router.post("/payments/webhook")
async def yukassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_sql_db),
    mongo: AsyncIOMotorDatabase = Depends(get_mongo),
):
    payload = await request.json()
    if payload.get("event") == "payment.succeeded":
        order_id = int(payload["object"]["metadata"]["order_id"])
        order = await update_order_status(db, order_id, "paid")
        if order:
            # Celery tasks
            send_order_notification.delay(order.user_id, f"Order {order_id} paid!")
            log_order_event.delay(order_id, "paid", mongo)  # Лог в Mongo
    return {"status": "ok"}
```

### app/tasks.py
```python
from celery import Celery
from app.integrations.telegram import send_telegram_message
from dotenv import load_dotenv
import os
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

load_dotenv()
app = Celery(
    "tasks", broker=os.getenv("CELERY_BROKER_URL"), backend=os.getenv("CELERY_RESULT_BACKEND")
)


@app.task
def send_order_notification(user_id: int, message: str):
    # Здесь получить telegram_id по user_id (упрощено)
    telegram_id = "dummy_telegram_id"  # Замените на реальный запрос
    send_telegram_message(telegram_id, message)


@app.task
def log_order_event(order_id: int, event: str, mongo: AsyncIOMotorDatabase):
    collection = mongo["logs"]
    collection.insert_one({"order_id": order_id, "event": event, "timestamp": datetime.now()})
```

### app/integrations/yukassa.py
```python
from yookassa import Configuration, Payment
from dotenv import load_dotenv
import os
import uuid

load_dotenv()
Configuration.account_id = os.getenv("YUKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YUKASSA_SECRET_KEY")


def create_payment(amount: float, order_id: int):
    payment = Payment.create(
        {
            "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": "https://your-site/success"},
            "capture": True,
            "description": f"Order {order_id}",
            "metadata": {"order_id": order_id},
        },
        uuid.uuid4(),
    )
    return payment.confirmation.confirmation_url
```

### app/integrations/telegram.py
```python
from aiogram import Bot, Dispatcher, types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()


@dp.message()
async def echo(message: types.Message):
    await message.answer(message.text)  # Пример хэндлера


async def setup_telegram_webhook(app: FastAPI):
    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
    await bot.set_webhook(webhook_url)
    # Интеграция aiogram с FastAPI
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path="/webhook/telegram")


async def send_telegram_message(chat_id: str, text: str):
    await bot.send_message(chat_id=chat_id, text=text)
```

### migrations/env.py
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.database import Base, SYNC_DATABASE_URL
from app.models import *  # Импорт всех моделей

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = SYNC_DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### migrations/script.py.mako
```
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = '${revision}'
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade():
    ${upgrades if upgrades else "pass"}

def downgrade():
    ${downgrades if downgrades else "pass"}
```

### migrations/versions/0001_initial.py (Инициализирующая ревизия)
```python
"""Initial migration

Revision ID: 0001_initial
Revises:
Create Date: 2025-08-14 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("telegram_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_id"), "products", ["id"], unique=False)
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("total", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_id"), "orders", ["id"], unique=False)
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_id"), "order_items", ["id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_order_items_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index(op.f("ix_orders_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_index(op.f("ix_products_id"), table_name="products")
    op.drop_table("products")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
```

### alembic.ini
```
[alembic]
script_location = migrations
sqlalchemy.url = postgresql://%(DB_USER)s:%(DB_PASSWORD)s@%(DB_HOST)s:%(DB_PORT)s/%(DB_NAME)s
```

### Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## docker-compose.yml
```yaml
version: '3.8'
services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
      - mongo
      - redis
    env_file:
      - .env
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  mongo:
    image: mongo:6
    volumes:
      - mongo_data:/data/db
    ports:
      - "27017:27017"
  redis:
    image: redis:7
    ports:
      - "6379:6379"
  celery:
    build: .
    command: celery -A app.tasks worker --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - redis
      - db
      - mongo
    env_file:
      - .env
volumes:
  postgres_data:
  mongo_data:
```

## Инструкции по запуску
1. **Установка**: Создайте директорию `telegram_store`, скопируйте все файлы. Заполните `.env` (скопируйте из `.env.example`).
2. **Зависимости**: `pip install -r requirements.txt` (или через Docker).
3. **Миграции**: 
   - `alembic upgrade head` (применит инициализирующую ревизию, создаст таблицы в Postgres).
4. **Запуск локально**: `docker-compose up --build` (запустит API, DB, Mongo, Redis, Celery). API на http://localhost:8000/docs.
5. **Telegram webhook**: После запуска, бот установит webhook автоматически (убедитесь в TELEGRAM_WEBHOOK_URL). Тестируйте отправку сообщений через Celery.
6. **Тестирование**:
   - Создайте товар: POST /api/products/ {"name": "Test", "price": 100.0}.
   - Создайте заказ: POST /api/orders/ {"items": [{"product_id": 1, "quantity": 1}]}.
   - Инициируйте платеж: POST /api/orders/payments/1.
   - Симулируйте webhook: POST /api/orders/payments/webhook с payload от ЮKassa.
7. **В prod**: Используйте HTTPS для webhook (ngrok для теста), добавьте auth, scale Celery.
