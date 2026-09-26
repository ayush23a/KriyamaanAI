import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.config import settings


class Base(DeclarativeBase):
    pass


# Async engine & session factory (used by FastAPI and runtime)
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None
_async_engine_loop: Any = None


def get_async_engine() -> AsyncEngine:
    global _async_engine, _async_session_factory, _async_engine_loop
    try:
        import asyncio
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if (
        _async_engine is None
        or (_async_engine_loop is not None and current_loop is not None and _async_engine_loop != current_loop)
    ):
        _async_engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )
        _async_session_factory = None
        _async_engine_loop = current_loop
    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_async_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Sync engine & session factory (used by Alembic and sync tools)
def get_sync_engine():
    return create_engine(
        settings.database_url_sync,
        echo=False,
        pool_pre_ping=True,
    )


def get_sync_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_sync_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

