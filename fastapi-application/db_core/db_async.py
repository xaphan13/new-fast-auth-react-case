from collections.abc import AsyncGenerator
from typing import Annotated

from core.config import SqliteDsn, settings
from fastapi import Depends
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class AsyncDbManager:
    def __init__(
        self,
        url: str,
        echo: bool = False,
        echo_pool: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        # Создание асинхронного движка SQLAlchemy
        # pool_size: размер пула подключений
        # max_overflow: максимальное количество дополнительных соединений
        self.engine: AsyncEngine = create_async_engine(
            url=url,
            echo=echo,
            echo_pool=echo_pool,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )

        if isinstance(settings.db.url, SqliteDsn):
            """Enable foreign key support for sqlite"""

            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        # Фабрика сессий для асинхронной работы с БД
        # autoflush=False — не отправлять изменения в БД до завершения транзакции
        # autocommit=False — отключить авто-подтверждение транзакций
        # expire_on_commit=False — сохранять состояние объектов после транзакции
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    async def engine_dispose(self) -> None:
        await self.engine.dispose()

    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


db_manager = AsyncDbManager(
    url=str(settings.db.url),
    echo=settings.db.echo,
    echo_pool=settings.db.echo_pool,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
)


CurrentSession = Annotated[AsyncSession, Depends(db_manager.get_async_session)]
