Сгенерировал стартовый репозиторий Telegram-магазина на FastAPI со стеком: FastAPI + SQLAlchemy (async) + Alembic + Postgres + Mongo (Motor) + Redis + Celery + Uvicorn. Оплата — ЮKassa, Telegram — aiogram v3 (webhook). Деплой — Docker Compose.

Ниже: структура, ключевые файлы (готовые к копипасте), docker-compose, миграции (инициализирующая ревизия), и инструкции по запуску.

Дерево проекта
```
telegram-shop/
├─ app/
│  ├─ main.py
│  ├─ core/
│  │  ├─ config.py
│  │  └─ logging.py
│  ├─ db/
│  │  ├─ postgres.py
│  │  ├─ mongo.py
│  │  └─ redis.py
│  ├─ models/
│  │  ├─ base.py
│  │  ├─ item.py
│  │  ├─ customer.py
│  │  ├─ order.py
│  │  └─ payment.py
│  ├─ schemas/
│  │  ├─ item.py
│  │  └─ order.py
│  ├─ api/
│  │  └─ v1/
│  │     ├─ api.py
│  │     └─ routes/
│  │        ├─ items.py
│  │        ├─ orders.py
│  │        └─ health.py
│  ├─ services/
│  │  ├─ inventory.py
│  │  ├─ payments/
│  │  │  └─ yookassa.py
│  │  └─ telegram/
│  │     ├─ bot.py
│  │     └─ router.py
│  └─ workers/
│     ├─ celery_app.py
│     └─ tasks/
│        ├─ telegram.py
│        └─ billing.py
├─ migrations/
│  ├─ env.py
│  └─ versions/
│     └─ 0001_init.py
├─ docker/
│  ├─ Dockerfile.api
│  ├─ Dockerfile.worker
│  └─ docker-compose.yml
├─ alembic.ini
├─ requirements.txt
├─ .env.example
├─ Makefile
└─ README.md
```

app/core/config.py
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_PREFIX: str = "/api/v1"

    POSTGRES_DSN: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/shop"
    MONGO_DSN: str = "mongodb://mongo:27017"
    REDIS_DSN: str = "redis://redis:6379/0"

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str
    PUBLIC_BASE_URL: str  # например, https://your-domain

    YOOKASSA_SHOP_ID: str
    YOOKASSA_SECRET_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()  # type: ignore
```

app/core/logging.py
```python
import logging
import sys


def setup_logging():
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format=fmt)
```

app/db/postgres.py
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.POSTGRES_DSN, pool_size=10, max_overflow=20, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

app/db/mongo.py
```python
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

mongo_client = AsyncIOMotorClient(settings.MONGO_DSN)
mongo_db = mongo_client["shop"]
```

app/db/redis.py
```python
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_DSN, decode_responses=True)
```

app/models/base.py
```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

app/models/item.py
```python
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000), default="")
    price_amount: Mapped[int] = mapped_column(Integer)  # копейки
    price_currency: Mapped[str] = mapped_column(String(3), default="RUB")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

app/models/customer.py
```python
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())
```

app/models/order.py
```python
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

OrderStatusEnum = Enum(
    "draft",
    "pending_payment",
    "paid",
    "cancelled",
    "fulfilled",
    name="order_status",
)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(OrderStatusEnum, default="pending_payment", index=True)
    total_amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    qty: Mapped[int]
    unit_price: Mapped[int]  # копейки
    subtotal: Mapped[int]  # копейки

    order: Mapped["Order"] = relationship(back_populates="items")
```

app/models/payment.py
```python
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

PaymentStatusEnum = Enum(
    "pending",
    "succeeded",
    "canceled",
    name="payment_status",
)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32), default="yookassa")
    provider_payment_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[str] = mapped_column(PaymentStatusEnum, default="pending", index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "provider_payment_id", name="uq_provider_payment"),
    )
```

app/schemas/item.py
```python
from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    sku: str = Field(..., max_length=64)
    title: str
    description: str = ""
    price_amount: int = Field(..., ge=0)
    price_currency: str = "RUB"
    active: bool = True


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price_amount: int | None = None
    price_currency: str | None = None
    active: bool | None = None


class ItemOut(BaseModel):
    id: int
    sku: str
    title: str
    description: str
    price_amount: int
    price_currency: str
    active: bool
```

app/schemas/order.py
```python
from pydantic import BaseModel


class OrderOut(BaseModel):
    id: int
    status: str
    total_amount: int
    currency: str
```

app/api/v1/api.py
```python
from fastapi import APIRouter
from app.api.v1.routes import items, orders, health

api_router = APIRouter()
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
```

app/api/v1/routes/health.py
```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/live")
async def live():
    return {"status": "live"}


@router.get("/ready")
async def ready():
    return {"status": "ready"}
```

app/api/v1/routes/items.py
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.postgres import SessionLocal
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate, ItemOut

router = APIRouter()


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@router.get("/", response_model=list[ItemOut])
async def list_items(session: AsyncSession = Depends(get_session)):
    rows = (
        (await session.execute(select(Item).where(Item.active == True).order_by(Item.id)))
        .scalars()
        .all()
    )
    return [ItemOut.model_validate(r.__dict__) for r in rows]


@router.post("/", response_model=ItemOut)
async def create_item(payload: ItemCreate, session: AsyncSession = Depends(get_session)):
    item = Item(**payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ItemOut.model_validate(item.__dict__)


@router.patch("/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: int, payload: ItemUpdate, session: AsyncSession = Depends(get_session)
):
    q = await session.execute(select(Item).where(Item.id == item_id))
    item = q.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    await session.commit()
    await session.refresh(item)
    return ItemOut.model_validate(item.__dict__)
```

app/api/v1/routes/orders.py
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.postgres import SessionLocal
from app.models.order import Order
from app.schemas.order import OrderOut

router = APIRouter()


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: int, session: AsyncSession = Depends(get_session)):
    q = await session.execute(select(Order).where(Order.id == order_id))
    o = q.scalar_one_or_none()
    if not o:
        raise HTTPException(404, "Order not found")
    return OrderOut.model_validate(
        {"id": o.id, "status": o.status, "total_amount": o.total_amount, "currency": o.currency}
    )
```

app/services/inventory.py
```python
# Заглушки для будущего резервирования/списания склада.
# Здесь можно реализовать Redis-локи и транзакции для конкурентной продажи.
```

app/services/payments/yookassa.py
```python
from uuid import uuid4
from yookassa import Configuration, Payment
from app.core.config import settings

# Инициализация один раз при импортe
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def create_payment_rub(
    amount_rub: str, description: str, return_url: str, metadata: dict, idem_key: str | None = None
):
    payload = {
        "amount": {"value": amount_rub, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": description,
        "metadata": metadata,
    }
    return Payment.create(payload, idempotency_key=idem_key or str(uuid4()))


def get_payment(payment_id: str):
    return Payment.find_one(payment_id)
```

app/services/telegram/bot.py
```python
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from app.core.config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
```

app/services/telegram/router.py
```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from app.db.postgres import SessionLocal
from app.db.redis import redis_client
from app.models.item import Item
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.services.payments import yookassa
from app.core.config import settings

router = Router()

CATALOG_PAGE_SIZE = 10


def kopecks_to_rub_str(value: int) -> str:
    return f"{value / 100:.2f}"


@router.message(F.text == "/start")
async def start(message: Message):
    # Зарегистрируем пользователя при первом заходе
    async with SessionLocal() as session:
        q = await session.execute(
            select(Customer).where(Customer.tg_user_id == message.from_user.id)
        )
        customer = q.scalar_one_or_none()
        if not customer:
            customer = Customer(
                tg_user_id=message.from_user.id,
                username=message.from_user.username or None,
            )
            session.add(customer)
            await session.commit()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть каталог", callback_data="catalog:0")],
            [InlineKeyboardButton(text="Корзина", callback_data="cart")],
        ]
    )
    await message.answer("Добро пожаловать в магазин! Выберите действие:", reply_markup=kb)


@router.callback_query(F.data.startswith("catalog:"))
async def show_catalog(cb: CallbackQuery):
    page = int(cb.data.split(":")[1])
    offset = page * CATALOG_PAGE_SIZE
    async with SessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(Item)
                    .where(Item.active == True)
                    .order_by(Item.id)
                    .offset(offset)
                    .limit(CATALOG_PAGE_SIZE)
                )
            )
            .scalars()
            .all()
        )
    if not rows:
        await cb.message.edit_text("Каталог пуст.")
        await cb.answer()
        return
    lines = [f"{i.id}. <b>{i.title}</b> — {kopecks_to_rub_str(i.price_amount)} ₽" for i in rows]
    buttons = [
        [InlineKeyboardButton(text=f"Добавить {i.id}", callback_data=f"add:{i.id}")] for i in rows
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="« Назад", callback_data=f"catalog:{page - 1}"))
    nav.append(InlineKeyboardButton(text="Корзина 🧺", callback_data="cart"))
    nav.append(InlineKeyboardButton(text="Вперёд »", callback_data=f"catalog:{page + 1}"))
    buttons.append(nav)
    await cb.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("add:"))
async def add_to_cart(cb: CallbackQuery):
    item_id = int(cb.data.split(":")[1])
    key = f"cart:{cb.from_user.id}"
    await redis_client.hincrby(key, str(item_id), 1)
    await cb.answer("Добавлено в корзину ✅", show_alert=False)


@router.callback_query(F.data == "cart")
async def show_cart(cb: CallbackQuery):
    key = f"cart:{cb.from_user.id}"
    items_map = await redis_client.hgetall(key)  # {item_id: qty}
    if not items_map:
        await cb.message.edit_text("Корзина пуста.")
        await cb.answer()
        return
    item_ids = [int(k) for k in items_map.keys()]
    async with SessionLocal() as session:
        rows = (await session.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
    totals = 0
    lines = []
    for it in rows:
        qty = int(items_map.get(str(it.id), 0))
        subtotal = it.price_amount * qty
        totals += subtotal
        lines.append(f"{it.title} × {qty} = {kopecks_to_rub_str(subtotal)} ₽")
    lines.append(f"\nИтого: <b>{kopecks_to_rub_str(totals)} ₽</b>")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оформить заказ и оплатить", callback_data="checkout")],
            [InlineKeyboardButton(text="Назад в каталог", callback_data="catalog:0")],
        ]
    )
    await cb.message.edit_text("\n".join(lines), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "checkout")
async def checkout(cb: CallbackQuery):
    key = f"cart:{cb.from_user.id}"
    items_map = await redis_client.hgetall(key)
    if not items_map:
        await cb.answer("Корзина пуста", show_alert=True)
        return

    async with SessionLocal() as session:
        # customer
        q = await session.execute(select(Customer).where(Customer.tg_user_id == cb.from_user.id))
        customer = q.scalar_one_or_none()
        if not customer:
            customer = Customer(tg_user_id=cb.from_user.id, username=cb.from_user.username or None)
            session.add(customer)
            await session.flush()

        # items
        item_ids = [int(k) for k in items_map.keys()]
        items = (await session.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
        if not items:
            await cb.answer("Товары не найдены", show_alert=True)
            return

        # compute totals
        total = 0
        order_items = []
        for it in items:
            qty = int(items_map.get(str(it.id), 0))
            subtotal = it.price_amount * qty
            order_items.append((it.id, qty, it.price_amount, subtotal))
            total += subtotal

        # create order
        order = Order(
            customer_id=customer.id, status="pending_payment", total_amount=total, currency="RUB"
        )
        session.add(order)
        await session.flush()  # get order.id

        # items
        for item_id, qty, unit_price, subtotal in order_items:
            session.add(
                OrderItem(
                    order_id=order.id,
                    item_id=item_id,
                    qty=qty,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )

        await session.commit()

    # create payment via YooKassa
    amount_str = f"{total / 100:.2f}"
    return_url = f"{settings.PUBLIC_BASE_URL}/thanks?order_id={order.id}"
    meta = {"order_id": order.id, "tg_user_id": cb.from_user.id}
    yp = yookassa.create_payment_rub(
        amount_rub=amount_str,
        description=f"Order #{order.id}",
        return_url=return_url,
        metadata=meta,
        idem_key=f"order-{order.id}",
    )

    # persist payment
    async with SessionLocal() as session:
        payment = Payment(
            order_id=order.id,
            provider="yookassa",
            provider_payment_id=yp.id,
            status="pending",
            amount=total,
            currency="RUB",
            idempotency_key=f"order-{order.id}",
        )
        session.add(payment)
        await session.commit()

    url = yp.confirmation.confirmation_url  # type: ignore[attr-defined]
    await cb.message.edit_text(
        f"Заказ #{order.id} создан. К оплате: <b>{kopecks_to_rub_str(total)} ₽</b>\n"
        f"Оплатите по ссылке: {url}"
    )
    await cb.answer()
```

app/workers/celery_app.py
```python
from celery import Celery
from app.core.config import settings

celery = Celery("shop", broker=settings.REDIS_DSN, backend=settings.REDIS_DSN)
celery.conf.task_routes = {
    "app.workers.tasks.*": {"queue": "default"},
}
```

app/workers/tasks/telegram.py
```python
import httpx
from app.core.config import settings
from app.workers.celery_app import celery


@celery.task(bind=True, max_retries=5, autoretry_for=(Exception,), retry_backoff=True)
def send_message(self, chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    r = httpx.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    r.raise_for_status()
```

app/workers/tasks/billing.py
```python
# Место для задач биллинга: напоминания об оплате, TTL резерва и т.п.
```

app/api/v1/routes for YooKassa webhook будет в main.py (см. ниже).

app/main.py
```python
from fastapi import FastAPI, Request, HTTPException
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.services.telegram.bot import bot, dp
from app.services.telegram.router import router as tg_router
from aiogram.types import Update
from app.db.mongo import mongo_db
from app.db.postgres import SessionLocal
from sqlalchemy import select
from app.models.payment import Payment
from app.models.order import Order
from app.workers.tasks.telegram import send_message
from app.services.payments import yookassa

setup_logging()

app = FastAPI(title="Telegram Shop")
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Подключаем Telegram-роутер к aiogram
dp.include_router(tg_router)


@app.post("/tg/webhook")
async def tg_webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="invalid telegram secret")
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.post("/webhooks/yookassa")
async def yookassa_webhook(request: Request):
    payload = await request.json()
    await mongo_db["webhooks_yookassa"].insert_one({"payload": payload})

    event_object = payload.get("object", {})
    payment_id = event_object.get("id")
    if not payment_id:
        raise HTTPException(400, "no payment_id")

    yp = yookassa.get_payment(payment_id)  # Подтверждение статуса у провайдера
    status = getattr(yp, "status", None)
    metadata = getattr(yp, "metadata", {}) or {}
    order_id = metadata.get("order_id")
    tg_user_id = metadata.get("tg_user_id")

    if not order_id:
        raise HTTPException(400, "no order_id in metadata")

    async with SessionLocal() as session:
        # Находим платеж
        q = await session.execute(select(Payment).where(Payment.provider_payment_id == payment_id))
        payment = q.scalar_one_or_none()
        if not payment:
            # idempotency: если почему-то не нашли — создадим запись
            payment = Payment(
                order_id=order_id,
                provider="yookassa",
                provider_payment_id=payment_id,
                status="pending",
                amount=event_object.get("amount", {}).get("value", 0),
                currency=event_object.get("amount", {}).get("currency", "RUB"),
            )
            session.add(payment)

        # Уже обработан
        if payment.status == "succeeded":
            return {"ok": True}

        if status == "succeeded":
            payment.status = "succeeded"
            # Обновляем заказ
            oq = await session.execute(select(Order).where(Order.id == order_id))
            order = oq.scalar_one_or_none()
            if order:
                order.status = "paid"
            await session.commit()

            # Уведомим пользователя
            if tg_user_id:
                send_message.delay(
                    int(tg_user_id), f"Оплата по заказу #{order_id} прошла успешно ✅"
                )
        elif status == "canceled":
            payment.status = "canceled"
            await session.commit()

    return {"ok": True}


@app.get("/")
async def root():
    return {"service": "telegram-shop", "docs": "/docs"}
```

migrations/env.py
```python
from __future__ import annotations
from logging.config import fileConfig
from pathlib import Path
import sys

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from alembic import context

# Добавим путь проекта для импорта app
BASE_DIR = Path(__file__).resolve().parents[1].parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.core.config import settings
from app.models.base import Base  # noqa
from app.models import item, customer, order, payment  # noqa

# this is the Alembic Config object, which provides access to values within the .ini file.
config = context.config
fileConfig(config.config_file_name)  # type: ignore

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.POSTGRES_DSN
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    assert configuration is not None
    configuration["sqlalchemy.url"] = settings.POSTGRES_DSN

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

migrations/versions/0001_init.py
```python
"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2025-08-13

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_customers_tg_user_id", "customers", ["tg_user_id"], unique=True)

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("price_amount", sa.Integer(), nullable=False),
        sa.Column("price_currency", sa.String(length=3), nullable=False, server_default="RUB"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_items_sku", "items", ["sku"], unique=True)
    op.create_index("ix_items_active", "items", ["active"], unique=False)

    op.execute(
        "CREATE TYPE order_status AS ENUM ('draft','pending_payment','paid','cancelled','fulfilled');"
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete=None)),
        sa.Column(
            "status",
            sa.Enum(name="order_status", create_type=False),
            nullable=False,
            server_default="pending_payment",
        ),
        sa.Column("total_amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="RUB"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE")),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id")),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Integer(), nullable=False),
    )

    op.execute("CREATE TYPE payment_status AS ENUM ('pending','succeeded','canceled');")
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE")),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="yookassa"),
        sa.Column("provider_payment_id", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.Enum(name="payment_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="RUB"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "provider_payment_id", name="uq_provider_payment"),
    )
    op.create_index(
        "ix_payments_provider_payment_id", "payments", ["provider_payment_id"], unique=True
    )
    op.create_index("ix_payments_status", "payments", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_provider_payment_id", table_name="payments")
    op.drop_table("payments")
    op.execute("DROP TYPE payment_status;")

    op.drop_table("order_items")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_table("orders")
    op.execute("DROP TYPE order_status;")

    op.drop_index("ix_items_active", table_name="items")
    op.drop_index("ix_items_sku", table_name="items")
    op.drop_table("items")

    op.drop_index("ix_customers_tg_user_id", table_name="customers")
    op.drop_table("customers")
```

docker/docker-compose.yml
```yaml
version: "3.9"
services:
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    env_file: ../.env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --reload
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - mongo
      - redis

  worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    env_file: ../.env
    command: celery -A app.workers.celery_app.celery worker -l info
    depends_on:
      - redis
      - postgres
      - mongo

  beat:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    env_file: ../.env
    command: celery -A app.workers.celery_app.celery beat -l info
    depends_on:
      - redis

  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: shop
    ports:
      - "5432:5432"

  mongo:
    image: mongo:6
    ports:
      - "27017:27017"

  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

docker/Dockerfile.api
```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

EXPOSE 8000
```

docker/Dockerfile.worker
```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app
```

alembic.ini
```ini
[alembic]
script_location = migrations
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@postgres:5432/shop

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = INFO
handlers = console

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
args = (sys.stdout,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(asctime)s %(levelname)-5.5s [%(name)s] %(message)s
```

requirements.txt
```
fastapi
uvicorn[standard]
sqlalchemy>=2.0
asyncpg
alembic
pydantic>=2
pydantic-settings
httpx
redis>=4
celery[redis]
motor
aiogram>=3
yookassa
python-multipart
prometheus-fastapi-instrumentator
```

.env.example
```
POSTGRES_DSN=postgresql+asyncpg://postgres:postgres@postgres:5432/shop
MONGO_DSN=mongodb://mongo:27017
REDIS_DSN=redis://redis:6379/0

TELEGRAM_BOT_TOKEN=0000000:XXXX
TELEGRAM_WEBHOOK_SECRET=your-secret-token
PUBLIC_BASE_URL=https://your-domain

YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
```

Makefile
```make
.PHONY: up down logs migrate setwebhook

up:
	cd docker && docker compose up -d --build

down:
	cd docker && docker compose down -v

logs:
	cd docker && docker compose logs -f api

migrate:
	# выполнить миграции внутри контейнера api
	cd docker && docker compose exec api alembic upgrade head

setwebhook:
	curl -sS -X POST "https://api.telegram.org/bot$${TELEGRAM_BOT_TOKEN}/setWebhook" \
	  -H "Content-Type: application/json" \
	  -d '{"url":"$${PUBLIC_BASE_URL}/tg/webhook","secret_token":"$${TELEGRAM_WEBHOOK_SECRET}"}'
```

README.md (кратко)
```markdown
# Telegram Shop (FastAPI + YooKassa)

Стек: FastAPI, SQLAlchemy (async), Alembic, Postgres, Redis, Mongo (Motor), Celery, Aiogram v3, YooKassa.

## Быстрый старт

1. Создайте .env
```bash
cp .env.example .env
# заполните TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, PUBLIC_BASE_URL, YOOKASSA_*
```

2. Поднимите контейнеры
```bash
make up
make migrate
```

3. Настройте webhook Telegram
```bash
make setwebhook
```

4. Зайдите в Swagger
- http://localhost:8000/docs

5. Создайте товары (POST /api/v1/items)
- затем в Telegram: /start → Каталог → Добавить → Корзина → Оформить → ссылка на оплату (ЮKassa)

## Webhooks
- Telegram: POST /tg/webhook (с заголовком X-Telegram-Bot-Api-Secret-Token = TELEGRAM_WEBHOOK_SECRET)
- YooKassa: POST /webhooks/yookassa (провайдер шлет события; статус подтверждаем через SDK)
```

Важно и что дальше
- В ЮKassa обязательно добавьте return_url в разрешенные URL в кабинете.
- Не забудьте в проде включить HTTPS и выставить PUBLIC_BASE_URL на ваш домен.
- Для админки можно быстро прикрутить sqladmin/fastapi-admin.
- Инвентарь/резервы можно расширить: Redis-локи + транзакции, TTL на резервы в Celery.

Готов доработать под ваши требования: добавить категории, промокоды, админ-панель, а также сценарии доставки/самовывоза.
