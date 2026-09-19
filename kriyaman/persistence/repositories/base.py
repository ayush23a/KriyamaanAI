from typing import Any, Generic, Sequence, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.db import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository for async SQLAlchemy CRUD operations."""

    def __init__(self, model_cls: type[ModelType], session: AsyncSession):
        self.model_cls = model_cls
        self.session = session

    async def get_by_id(self, id_: str) -> ModelType | None:
        result = await self.session.execute(
            select(self.model_cls).where(self.model_cls.id == id_)
        )
        return result.scalars().first()

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelType]:
        result = await self.session.execute(
            select(self.model_cls).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def create(self, **kwargs: Any) -> ModelType:
        instance = self.model_cls(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.session.delete(instance)
        await self.session.flush()

