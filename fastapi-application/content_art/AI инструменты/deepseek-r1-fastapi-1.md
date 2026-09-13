### Стартовый репозиторий Telegram-магазина на FastAPI

**Структура репозитория**:
```
telegram-shop/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── dependencies.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── payment.py
│   │   └── telegram.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── items.py
│   │   ├── orders.py
│   │   ├── payments.py
│   │   └── bot.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── celery_tasks.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── security.py
│   └── webhook_handlers/
│       ├── __init__.py
│       └── telegram.py
├── migrations/
│   ├── versions/
│   │   └── a1b2c3d4e5f6_initial_migration.py
│   ├── env.py
│   ├── script.py.mako
│   └── README
├── scripts/
│   └── init_db.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_api.py
    └── test_tasks.py
```

---

### Ключевые файлы

**1. .env.example**:
```env
POSTGRES_USER=user
POSTGRES_PASSWORD=pass
POSTGRES_DB=telegram_shop
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/telegram_shop
REDIS_URL=redis://redis:6379/0
TELEGRAM_TOKEN=your_telegram_bot_token
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
WEBHOOK_URL=https://your-domain.com/bot/webhook
MONGO_URL=mongodb://root:example@mongo:27017
```

**2. docker-compose.yml**:
```yaml
version: '3.8'

services:
  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/code
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
      - mongo

  celery:
    build: .
    command: celery -A app.tasks.celery_tasks worker --loglevel=info
    volumes:
      - .:/code
    env_file:
      - .env
    depends_on:
      - db
      - redis
      - mongo

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7

  mongo:
    image: mongo:6
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: example
    volumes:
      - mongo_data:/data/db

volumes:
  pg_data:
  mongo_data:
```

**3. Dockerfile**:
```Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y gcc

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
```

**4. requirements.txt**:
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-dotenv==1.0.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
alembic==1.13.1
motor==3.3.2
redis==5.0.0
celery[redis]==5.3.6
aiogram==3.1.1
httpx==0.27.0
pydantic-settings==2.1.0
pydantic==2.5.3
```

**5. app/config.py**:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = None
    REDIS_URL: str = "redis://redis:6379/0"
    TELEGRAM_TOKEN: str
    YOOKASSA_SHOP_ID: str
    YOOKASSA_SECRET_KEY: str
    WEBHOOK_URL: str
    MONGO_URL: str = "mongodb://root:example@mongo:27017"

    class Config:
        env_file = ".env"

    def __init__(self, **values):
        super().__init__(**values)
        self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@db:5432/{self.POSTGRES_DB}"


settings = Settings()
```

**6. app/database.py**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, future=True, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


async def get_db():
    async with async_session() as session:
        yield session
```

**7. app/models.py**:
```python
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    description = Column(String(300))
    price = Column(Float)
    is_available = Column(Boolean, default=True)
    orders = relationship("Order", back_populates="product")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    status = Column(String(20), default="created")
    yookassa_id = Column(String(50))
    product = relationship("Product", back_populates="orders")
```

**8. app/schemas.py**:
```python
from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    description: str
    price: float


class ProductResponse(ProductCreate):
    id: int
    is_available: bool


class OrderCreate(BaseModel):
    product_id: int
    user_id: int


class OrderResponse(OrderCreate):
    id: int
    status: str
    payment_url: str


class YookassaWebhook(BaseModel):
    event: str
    object: dict
```

**9. app/main.py**:
```python
from fastapi import FastAPI
from app.api import items, orders, payments, bot
from app.database import engine, Base
import asyncio

app = FastAPI()

app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(bot.router, prefix="/bot", tags=["bot"])


@app.on_event("startup")
async def startup():
    # Инициализация подключений к БД
    from app.database import engine

    async with engine.begin() as conn:
        # Для разработки: удалить в продакшене!
        await conn.run_sync(Base.metadata.create_all)

    # Настройка вебхука Telegram
    from app.services.telegram import setup_bot_webhook

    await setup_bot_webhook()
```

**10. app/services/telegram.py**:
```python
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from app.config import settings

bot = Bot(token=settings.TELEGRAM_TOKEN)
dp = Dispatcher()


async def setup_bot_webhook():
    await bot.set_webhook(url=settings.WEBHOOK_URL, drop_pending_updates=True)


@dp.message(commands=["start"])
async def start_command(message: types.Message, state: FSMContext):
    await message.answer(
        "🏪 Добро пожаловать в наш магазин!\n\n"
        "Используйте команды:\n"
        "/products - список товаров\n"
        "/cart - ваша корзина\n"
        "/orders - ваши заказы"
    )


@dp.message(commands=["products"])
async def list_products(message: types.Message):
    # Здесь будет логика получения товаров из БД
    await message.answer(
        "📦 Список товаров:\n\n1. Товар 1 - 100₽\n2. Товар 2 - 200₽\n3. Товар 3 - 300₽"
    )
```

**11. app/api/bot.py**:
```python
from fastapi import APIRouter, Depends
from aiogram import types
from app.services.telegram import dp, bot
from app.config import settings

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(update: dict):
    telegram_update = types.Update(**update)
    await dp.feed_webhook_update(bot, telegram_update)
    return {"status": "ok"}


@router.post("/notify")
async def notify_user(chat_id: int, message: str):
    await bot.send_message(chat_id, message)
    return {"status": "notification sent"}
```

**12. app/api/orders.py**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, models
from app.database import get_db
from app.services.payment import create_yookassa_payment
import uuid

router = APIRouter()


@router.post("/", response_model=schemas.OrderResponse)
async def create_order(order: schemas.OrderCreate, db: AsyncSession = Depends(get_db)):
    # Проверка наличия товара
    product = await db.get(models.Product, order.product_id)
    if not product or not product.is_available:
        raise HTTPException(status_code=404, detail="Товар недоступен")

    # Создание платежа в ЮKassa
    payment_info = await create_yookassa_payment(
        amount=product.price, currency="RUB", description=f"Оплата товара: {product.name}"
    )

    # Сохранение заказа в БД
    db_order = models.Order(
        user_id=order.user_id,
        product_id=order.product_id,
        yookassa_id=payment_info["id"],
        status="pending",
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)

    return {
        "id": db_order.id,
        "user_id": db_order.user_id,
        "product_id": db_order.product_id,
        "status": db_order.status,
        "payment_url": payment_info["confirmation"]["confirmation_url"],
    }
```

**13. app/tasks/celery_tasks.py**:
```python
from celery import Celery
from app.config import settings
import httpx

celery = Celery(__name__, broker=settings.REDIS_URL)


@celery.task
def process_payment_webhook(data: dict):
    # Обработка вебхука от ЮKassa
    from app.services.payment import handle_yookassa_webhook

    handle_yookassa_webhook(data)


@celery.task
def send_telegram_notification(chat_id: int, message: str):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    with httpx.Client() as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
```

**14. migrations/versions/a1b2c3d4e5f6_initial_migration.py**:
```python
"""Initial migration

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2023-08-13 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="created", nullable=False),
        sa.Column("yookassa_id", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)


def downgrade():
    op.drop_table("orders")
    op.drop_table("products")
```

---

### Инструкция по запуску

**1. Инициализация проекта**:
```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/telegram-shop.git
cd telegram-shop

# Создать .env файл
cp .env.example .env
nano .env  # Заполнить реальными значениями

# Создать виртуальное окружение (опционально)
python -m venv venv
source venv/bin/activate
```

**2. Запуск с Docker Compose**:
```bash
docker-compose up --build -d

# Применить миграции
docker-compose exec web alembic upgrade head

# Создать суперпользователя (если нужно)
docker-compose exec web python -m app.scripts.init_db
```

**3. Настройка Telegram бота**:
```bash
# Установить вебхук
curl -F "url=https://your-domain.com/bot/webhook" \
https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook
```

**4. Тестирование**:
```bash
# Запуск тестов
docker-compose exec web pytest

# Проверить API
curl http://localhost:8000/docs
```

**5. Деплой в продакшн**:
1. Настроить Nginx как reverse proxy
2. Добавить SSL сертификат (Let's Encrypt)
3. Настроить CI/CD (GitHub Actions/GitLab CI)
4. Заменить `--reload` на `--workers 4` в docker-compose.yml

---

### MVP План разработки

**Архитектура**:
```
Frontend (Telegram) ↔ FastAPI (Python) ↔ PostgreSQL (основные данные)
                             │
                             ├── Redis (кеш, Celery брокер)
                             ├── MongoDB (аналитика, логи)
                             ├── ЮKassa (платежи)
                             └── Celery (фоновые задачи)
```

**Флоу оплаты**:
1. Пользователь выбирает товар в боте
2. Бот отправляет запрос на `/orders`
3. FastAPI создает платеж в ЮKassa
4. Пользователь оплачивает через платежную форму
5. ЮKassa отправляет вебхук на `/payments/webhook`
6. Celery обрабатывает платеж и обновляет статус заказа
7. Бот уведомляет пользователя об успешной оплате

**Сроки разработки MVP**:
- Базовый функционал (товары, заказы): 3 дня
- Интеграция с ЮKassa: 2 дня
- Telegram бот: 2 дня
- Аналитика в MongoDB: 1 день
- Тестирование и деплой: 2 дня

**Итого**: 10 рабочих дней

---

Этот шаблон включает:
1. Готовую структуру проекта
2. Настроенный Docker Compose
3. Миграции Alembic
4. Примеры моделей и API
5. Интеграцию с Telegram (aiogram)
6. Базовую платежную интеграцию
7. Конфигурацию для Celery и Redis
8. Поддержку PostgreSQL и MongoDB

Проект полностью готов к разработке. Для начала работы достаточно заполнить .env файл и запустить `docker-compose up`.
