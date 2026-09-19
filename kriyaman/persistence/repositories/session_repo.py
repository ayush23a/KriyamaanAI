from typing import Any, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.models import SessionModel


class SessionRepository:
    """Repository for managing user sessions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, session_id: str) -> SessionModel | None:
        result = await self.session.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        return result.scalars().first()

    async def list_by_principal(
        self, memory_principal_id: str, limit: int = 50, offset: int = 0
    ) -> Sequence[SessionModel]:
        result = await self.session.execute(
            select(SessionModel)
            .where(SessionModel.memory_principal_id == memory_principal_id)
            .order_by(SessionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def create(
        self,
        memory_principal_id: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> SessionModel:
        kwargs: dict[str, Any] = {
            "memory_principal_id": memory_principal_id,
            "title": title,
            "metadata_json": metadata or {},
        }
        if session_id:
            kwargs["id"] = session_id
        session_obj = SessionModel(**kwargs)
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def update_title(self, session_id: str, title: str) -> SessionModel | None:
        session_obj = await self.get_by_id(session_id)
        if session_obj:
            session_obj.title = title
            await self.session.flush()
        return session_obj

