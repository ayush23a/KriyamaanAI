from typing import Any, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.models import MemoryModel


class MemoryRepository:
    """Repository for managing explicit long-term memories with pgvector embeddings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, memory_id: str) -> MemoryModel | None:
        result = await self.session.execute(
            select(MemoryModel).where(MemoryModel.id == memory_id)
        )
        return result.scalars().first()

    async def get_by_id_and_user(self, memory_id: str, user_id: str) -> MemoryModel | None:
        result = await self.session.execute(
            select(MemoryModel)
            .where(MemoryModel.id == memory_id)
            .where(MemoryModel.user_id == user_id)
        )
        return result.scalars().first()

    async def create_explicit(
        self,
        memory_principal_id: str,
        kind: str,
        content: str,
        embedding: list[float] | None = None,
        source_turn_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> MemoryModel:
        memory = MemoryModel(
            memory_principal_id=memory_principal_id,
            user_id=user_id,
            kind=kind,
            content=content,
            embedding=embedding,
            source_turn_id=source_turn_id,
            explicit=True,
            metadata_json=metadata or {},
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def search_similar(
        self,
        memory_principal_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        user_id: str | None = None,
    ) -> list[tuple[MemoryModel, float]]:
        """Search memories scoped to a memory principal and user using cosine similarity."""
        distance_expr = MemoryModel.embedding.cosine_distance(query_embedding).label("distance")

        stmt = (
            select(MemoryModel, distance_expr)
            .where(MemoryModel.memory_principal_id == memory_principal_id)
            .where(MemoryModel.status == "active")
            .where(MemoryModel.embedding.is_not(None))
        )
        if user_id:
            stmt = stmt.where(MemoryModel.user_id == user_id)

        stmt = stmt.order_by(distance_expr.asc()).limit(top_k)

        result = await self.session.execute(stmt)
        rows = result.all()

        results: list[tuple[MemoryModel, float]] = []
        for mem, distance in rows:
            score = max(0.0, min(1.0, 1.0 - float(distance)))
            results.append((mem, score))

        return results

    async def list_by_principal(
        self, memory_principal_id: str, limit: int = 50, user_id: str | None = None
    ) -> Sequence[MemoryModel]:
        stmt = (
            select(MemoryModel)
            .where(MemoryModel.memory_principal_id == memory_principal_id)
            .where(MemoryModel.status == "active")
        )
        if user_id:
            stmt = stmt.where(MemoryModel.user_id == user_id)
        stmt = stmt.order_by(MemoryModel.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(
        self, user_id: str, limit: int = 50
    ) -> Sequence[MemoryModel]:
        stmt = (
            select(MemoryModel)
            .where(MemoryModel.user_id == user_id)
            .where(MemoryModel.status == "active")
            .order_by(MemoryModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete(self, memory_id: str) -> bool:
        mem = await self.get_by_id(memory_id)
        if mem:
            await self.session.delete(mem)
            await self.session.flush()
            return True
        return False

    async def delete_for_user(self, memory_id: str, user_id: str) -> bool:
        mem = await self.get_by_id_and_user(memory_id, user_id)
        if mem:
            await self.session.delete(mem)
            await self.session.flush()
            return True
        return False

