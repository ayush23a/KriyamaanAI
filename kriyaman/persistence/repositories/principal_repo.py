from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.models import MemoryPrincipalModel


class MemoryPrincipalRepository:
    """Repository for managing anonymous logical memory principals."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, principal_id: str) -> MemoryPrincipalModel | None:
        result = await self.session.execute(
            select(MemoryPrincipalModel).where(MemoryPrincipalModel.id == principal_id)
        )
        return result.scalars().first()

    async def get_by_namespace_key(self, namespace_key: str) -> MemoryPrincipalModel | None:
        result = await self.session.execute(
            select(MemoryPrincipalModel).where(MemoryPrincipalModel.namespace_key == namespace_key)
        )
        return result.scalars().first()

    async def get_or_create(
        self, namespace_key: str, kind: str = "anonymous", metadata: dict[str, Any] | None = None
    ) -> MemoryPrincipalModel:
        principal = await self.get_by_namespace_key(namespace_key)
        if principal:
            return principal
        principal = MemoryPrincipalModel(
            namespace_key=namespace_key,
            kind=kind,
            metadata_json=metadata or {},
        )
        self.session.add(principal)
        await self.session.flush()
        return principal

