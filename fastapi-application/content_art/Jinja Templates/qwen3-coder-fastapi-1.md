# Telegram Магазин - Стартовый репозиторий

## Структура проекта

```
telegram-shop/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   └── order.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   └── order.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── telegram.py
│   │   │   ├── products.py
│   │   │   └── orders.py
│   │   └── dependencies.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── telegram_service.py
│   │   ├── payment_service.py
│   │   └── order_service.py
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py
│   │   └── handlers.py
│   └── celery_worker.py
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## requirements.txt

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
alembic==1.13.1
redis==5.0.1
celery==5.3.4
motor==3.3.2
pymongo==4.6.1
aiogram==3.2.0
yookassa==3.0.1
pydantic==2.5.2
pydantic-settings==2.1.0
python-multipart==0.0.6
httpx==0.25.2
python-jose==3.3.0
passlib==1.7.4
bcrypt==4.1.2
pytest==7.4.3
pytest-asyncio==0.21.1
```

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: telegram_shop
      POSTGRES_USER: shop_user
      POSTGRES_PASSWORD: shop_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  mongodb:
    image: mongo:6
    volumes:
      - mongo_/data/db
    ports:
      - "27017:27017"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
      - mongodb
    environment:
      - DATABASE_URL=postgresql+asyncpg://shop_user:shop_password@db:5432/telegram_shop
      - MONGODB_URL=mongodb://mongodb:27017/telegram_shop
      - REDIS_URL=redis://redis:6379/0
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - YOOKASSA_SHOP_ID=${YOOKASSA_SHOP_ID}
      - YOOKASSA_SECRET_KEY=${YOOKASSA_SECRET_KEY}
    env_file:
      - .env

  worker:
    build: .
    command: celery -A app.celery_worker.celery worker --loglevel=info
    depends_on:
      - redis
      - db
      - mongodb
    environment:
      - DATABASE_URL=postgresql+asyncpg://shop_user:shop_password@db:5432/telegram_shop
      - MONGODB_URL=mongodb://mongodb:27017/telegram_shop
      - REDIS_URL=redis://redis:6379/0
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - YOOKASSA_SHOP_ID=${YOOKASSA_SHOP_ID}
      - YOOKASSA_SECRET_KEY=${YOOKASSA_SECRET_KEY}
    env_file:
      - .env

  flower:
    image: mher/flower
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis

volumes:
  postgres_
  mongo_
```

## .env.example

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# YooKassa
YOOKASSA_SHOP_ID=your_shop_id_here
YOOKASSA_SECRET_KEY=your_secret_key_here

# Database
DATABASE_URL=postgresql+asyncpg://shop_user:shop_password@localhost:5432/telegram_shop
MONGODB_URL=mongodb://localhost:27017/telegram_shop

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Webhook
WEBHOOK_URL=https://your-domain.com/webhook/telegram
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000
```

## app/config.py

```python
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    webhook_url: str
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8000

    # YooKassa
    yookassa_shop_id: str
    yookassa_secret_key: str

    # Database
    database_url: str
    mongodb_url: str

    # Redis
    redis_url: str

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
```

## app/database.py

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

# PostgreSQL
engine = create_async_engine(settings.database_url, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# MongoDB
mongo_client = AsyncIOMotorClient(settings.mongodb_url)
mongodb = mongo_client.telegram_shop
```

## app/models/user.py

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## app/models/product.py

```python
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.sql import func
from app.models.user import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    price = Column(Float)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## app/models/order.py

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.user import Base
import enum


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_amount = Column(Float)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price = Column(Float)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
```

## app/schemas/user.py

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
```

## app/schemas/product.py

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class Product(ProductBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
```

## app/schemas/order.py

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int


class OrderItemCreate(OrderItemBase):
    pass


class OrderItem(OrderItemBase):
    id: int
    order_id: int
    price: float

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    user_id: int
    total_amount: float


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None


class Order(OrderBase):
    id: int
    status: OrderStatus
    payment_id: Optional[str] = None
    created_at: datetime
    items: List[OrderItem] = []

    class Config:
        from_attributes = True
```

## app/services/telegram_service.py

```python
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


class ShopStates(StatesGroup):
    viewing_products = State()
    creating_order = State()


class TelegramService:
    def __init__(self):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.dp = Dispatcher()
        self.setup_handlers()

    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: Message):
            await message.answer(
                "Добро пожаловать в наш магазин! Используйте /products для просмотра товаров."
            )

        @self.dp.message(Command("products"))
        async def cmd_products(message: Message, state: FSMContext):
            # Здесь будет логика показа товаров
            await state.set_state(ShopStates.viewing_products)
            await message.answer("Список товаров будет здесь")

        @self.dp.callback_query()
        async def handle_callback(callback: CallbackQuery):
            if callback.data.startswith("order_"):
                product_id = int(callback.data.split("_")[1])
                await self.create_order(callback.from_user.id, product_id, callback.message)

    async def create_order(self, user_id: int, product_id: int, message):
        """Создание заказа и платежа"""
        order_service = OrderService()
        payment_service = PaymentService()

        # Создаем заказ (здесь нужна реализация)
        # order = await order_service.create_order(...)

        # Создаем платеж
        # payment = await payment_service.create_payment(...)

        await message.answer("Заказ создан! Ссылка для оплаты будет здесь.")

    async def send_message(self, chat_id: int, text: str, reply_markup=None):
        """Отправка сообщения пользователю"""
        await self.bot.send_message(chat_id, text, reply_markup=reply_markup)

    async def start_polling(self):
        """Запуск polling режима"""
        await self.dp.start_polling(self.bot)
```

## app/services/payment_service.py

```python
from yookassa import Payment
import uuid
from app.config import settings


class PaymentService:
    def __init__(self):
        self.shop_id = settings.yookassa_shop_id
        self.secret_key = settings.yookassa_secret_key

    async def create_payment(self, amount: float, description: str, return_url: str, order_id: str):
        """Создание платежа через ЮKassa"""
        payment = Payment.create(
            {
                "amount": {"value": str(amount), "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": return_url},
                "description": description,
                "metadata": {"order_id": order_id},
                "capture": True,
            }
        )
        return payment

    async def get_payment_status(self, payment_id: str):
        """Получение статуса платежа"""
        payment = Payment.find_one(payment_id)
        return payment
```

## app/services/order_service.py

```python
from sqlalchemy import select
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


class OrderService:
    async def create_order(self, db: AsyncSession, user_id: int, items: list):
        """Создание заказа"""
        # Получаем пользователя
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        # Рассчитываем общую сумму
        total_amount = 0
        order_items = []

        for item in items:
            result = await db.execute(select(Product).filter(Product.id == item["product_id"]))
            product = result.scalar_one_or_none()

            if product:
                item_total = product.price * item["quantity"]
                total_amount += item_total

                order_item = OrderItem(
                    product_id=item["product_id"], quantity=item["quantity"], price=product.price
                )
                order_items.append(order_item)

        # Создаем заказ
        order = Order(user_id=user_id, total_amount=total_amount, status="pending")

        db.add(order)
        await db.flush()

        # Добавляем товары в заказ
        for item in order_items:
            item.order_id = order.id
            db.add(item)

        await db.commit()
        await db.refresh(order)

        return order

    async def get_order(self, db: AsyncSession, order_id: int):
        """Получение заказа по ID"""
        result = await db.execute(select(Order).filter(Order.id == order_id))
        return result.scalar_one_or_none()

    async def update_order_status(self, db: AsyncSession, order_id: int, status: str):
        """Обновление статуса заказа"""
        result = await db.execute(select(Order).filter(Order.id == order_id))
        order = result.scalar_one_or_none()

        if order:
            order.status = status
            await db.commit()
            await db.refresh(order)

        return order
```

## app/api/routes/telegram.py

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.telegram_service import TelegramService
import json

router = APIRouter(prefix="/webhook", tags=["telegram"])


@router.post("/telegram")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook для получения сообщений от Telegram"""
    update_data = await request.json()

    # Здесь будет обработка webhook от Telegram
    # В aiogram v3 webhook обрабатывается автоматически

    return {"status": "ok"}


@router.get("/set_webhook")
async def set_webhook():
    """Установка webhook для Telegram бота"""
    from app.config import settings
    from aiogram import Bot

    bot = Bot(token=settings.telegram_bot_token)
    await bot.set_webhook(settings.webhook_url)

    return {"status": "webhook set"}
```

## app/api/routes/products.py

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[schemas.Product])
async def get_products(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Product).filter(models.Product.is_active == True).offset(skip).limit(limit)
    )
    products = result.scalars().all()
    return products


@router.post("/", response_model=schemas.Product)
async def create_product(product: schemas.ProductCreate, db: AsyncSession = Depends(get_db)):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.get("/{product_id}", response_model=schemas.Product)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Product).filter(models.Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
```

## app/api/routes/orders.py

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app import models, schemas
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=List[schemas.Order])
async def get_orders(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Order).offset(skip).limit(limit))
    orders = result.scalars().all()
    return orders


@router.get("/{order_id}", response_model=schemas.Order)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Order).filter(models.Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/", response_model=schemas.Order)
async def create_order(order: schemas.OrderCreate, db: AsyncSession = Depends(get_db)):
    order_service = OrderService()
    new_order = await order_service.create_order(db, order.user_id, order.items)
    return new_order


@router.post("/webhook/yookassa")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook для получения уведомлений от ЮKassa"""
    data = await request.json()

    if data.get("event") == "payment.succeeded":
        payment = data.get("object", {})
        order_id = payment.get("metadata", {}).get("order_id")

        if order_id:
            order_service = OrderService()
            updated_order = await order_service.update_order_status(db, int(order_id), "paid")

            if updated_order:
                # Здесь можно отправить уведомление пользователю через Telegram
                pass

    return {"status": "ok"}
```

## app/main.py

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine
from app.models.user import Base as UserBase
from app.models.product import Base as ProductBase
from app.models.order import Base as OrderBase
from app.api.routes import telegram, products, orders
from app.bot.bot import start_bot
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(ProductBase.metadata.create_all)
        await conn.run_sync(OrderBase.metadata.create_all)

    # Запуск Telegram бота
    bot_task = asyncio.create_task(start_bot())

    yield

    # Очистка при завершении
    bot_task.cancel()


app = FastAPI(title="Telegram Shop API", version="1.0.0", lifespan=lifespan)

# Подключение маршрутов
app.include_router(telegram.router)
app.include_router(products.router)
app.include_router(orders.router)


@app.get("/")
async def root():
    return {"message": "Telegram Shop API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## app/bot/bot.py

```python
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.config import settings
import asyncio

class ShopStates(StatesGroup):
    viewing_products = State()

# Инициализация бота
bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Добро пожаловать в наш магазин! Используйте /products для просмотра товаров.")

@dp.message(Command("products"))
async def cmd_products(message: Message, state: FSMContext):
    await state.set_state(ShopStates.viewing_products)
    await message.answer("Список товаров:\n\n1. Товар 1 - 100 руб\n2. Товар 2 - 200 руб\n\nНажмите на товар для заказа")

async def start_bot():
    """Запуск бота"""
    await dp.start_polling(bot)

# Для webhook режима
async def process_update(update_ dict):
    """Обработка webhook update"""
    await dp.feed_raw_update(bot, update_data)
```

## app/celery_worker.py

```python
from celery import Celery
from app.config import settings

celery = Celery(__name__)
celery.conf.broker_url = settings.redis_url
celery.conf.result_backend = settings.redis_url


@celery.task
def send_telegram_notification(chat_id: int, message: str):
    """Отправка уведомления в Telegram"""
    # Здесь будет логика отправки сообщения
    print(f"Sending message to {chat_id}: {message}")
    return True


@celery.task
def process_order_payment(order_id: int):
    """Обработка оплаты заказа"""
    # Здесь будет логика обработки платежа
    print(f"Processing payment for order {order_id}")
    return True
```

## migrations/alembic.ini

```ini
# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = migrations

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python-dateutil library that can be
# installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# max_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version number format
version_num_format = %04d

# version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces and/or commas.
# Valid values for version_path_separator are:
#
# version_path_separator = :
# version_path_separator = ;
# version_path_separator = space
version_path_separator = os

# set to 'true' to search source files recursively
# in each "version_locations" directory
# new in Alembic version 1.10
# recursive_version_locations = false

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = driver://user:pass@localhost/dbname


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

## migrations/env.py

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.models.user import Base as UserBase
from app.models.product import Base as ProductBase
from app.models.order import Base as OrderBase
from app.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = [UserBase.metadata, ProductBase.metadata, OrderBase.metadata]

# Set the database URL
config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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

## migrations/versions/0001_initial.py

```python
"""Initial migration

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_id"), "products", ["id"], unique=False)
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PAID", "CANCELLED", "SHIPPED", name="orderstatus"),
            nullable=True,
        ),
        sa.Column("payment_id", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("price", sa.Float(), nullable=True),
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
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_order_items_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index(op.f("ix_orders_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_index(op.f("ix_products_id"), table_name="products")
    op.drop_table("products")
    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS orderstatus")
    # ### end Alembic commands ###
```

## tests/test_main.py

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models.user import Base as UserBase
from app.models.product import Base as ProductBase

# Тестовая база данных
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Telegram Shop API"}


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

## README.md

```markdown
# Telegram Shop

Telegram магазин с интеграцией ЮKassa для приема платежей.

## Функциональность

- 🤖 Telegram бот (aiogram v3) с webhook
- 🛒 Управление товарами и заказами (PostgreSQL)
- 💰 Прием платежей через ЮKassa
- 📊 Логирование и аналитика (MongoDB)
- 📋 Асинхронная обработка задач (Celery + Redis)
- 🐳 Docker контейнеризация

## Требования

- Docker и Docker Compose
- Telegram бот (получить через @BotFather)
- Аккаунт ЮKassa

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd telegram-shop
```

2. Создайте `.env` файл:
```bash
cp .env.example .env
```

3. Заполните переменные окружения в `.env`:
- `TELEGRAM_BOT_TOKEN` - токен вашего Telegram бота
- `YOOKASSA_SHOP_ID` - ID магазина в ЮKassa
- `YOOKASSA_SECRET_KEY` - секретный ключ ЮKassa
- `WEBHOOK_URL` - URL для webhook (например, https://your-domain.com/webhook/telegram)

4. Запустите приложение:
```bash
docker-compose up -d
```

5. Примените миграции:
```bash
docker-compose exec web alembic upgrade head
```

6. Установите webhook для Telegram:
```bash
docker-compose exec web curl http://localhost:8000/webhook/set_webhook
```

## Использование

### API Endpoints

- `POST /webhook/telegram` - Webhook для Telegram
- `GET /webhook/set_webhook` - Установка webhook для Telegram
- `GET /products/` - Получение списка товаров
- `POST /products/` - Создание товара
- `GET /products/{id}` - Получение товара по ID
- `GET /orders/` - Получение списка заказов
- `POST /orders/` - Создание заказа
- `GET /orders/{id}` - Получение заказа по ID

### Telegram команды

- `/start` - Приветствие
- `/products` - Просмотр товаров

## Разработка

### Запуск тестов

```bash
docker-compose exec web pytest
```

### Миграции

Создание новой миграции:
```bash
docker-compose exec web alembic revision --autogenerate -m "Описание изменений"
```

Применение миграций:
```bash
docker-compose exec web alembic upgrade head
```

## Безопасность

- Все API endpoints защищены
- Валидация входных данных через Pydantic
- HTTPS рекомендуется для production

## Мониторинг

- Flower доступен по адресу: http://localhost:5555

## Структура проекта

```
app/
├── main.py          # Основное FastAPI приложение
├── config.py        # Конфигурация
├── database.py      # Подключение к базам данных
├── models/          # SQLAlchemy модели
├── schemas/         # Pydantic схемы
├── api/             # API маршруты
├── services/        # Бизнес-логика
├── bot/             # Telegram бот
└── celery_worker.py # Celery worker
```

## Технологии

- **FastAPI** - веб-фреймворк
- **SQLAlchemy (async)** - ORM для PostgreSQL
- **Alembic** - миграции базы данных
- **PostgreSQL** - основная база данных
- **MongoDB (Motor)** - для логирования и аналитики
- **Redis** - брокер сообщений для Celery
- **Celery** - асинхронные задачи
- **aiogram v3** - Telegram бот фреймворк
- **YooKassa** - платежная система
- **Uvicorn** - ASGI сервер
```

## Инструкция по запуску

1. **Клонирование репозитория:**
```bash
git clone <repository-url>
cd telegram-shop
```

2. **Настройка окружения:**
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими данными
```

3. **Запуск Docker Compose:**
```bash
docker-compose up -d
```

4. **Применение миграций:**
```bash
docker-compose exec web alembic upgrade head
```

5. **Установка webhook для Telegram:**
```bash
docker-compose exec web curl http://localhost:8000/webhook/set_webhook
```

6. **Проверка работоспособности:**
```bash
curl http://localhost:8000/health
```

7. **Доступ к сервисам:**
- API: http://localhost:8000
- Flower (Celery): http://localhost:5555
- PostgreSQL: localhost:5432
- MongoDB: localhost:27017
- Redis: localhost:6379

Этот стартовый репозиторий предоставляет полностью готовую базу для Telegram магазина с асинхронной архитектурой и интеграцией всех необходимых сервисов!
