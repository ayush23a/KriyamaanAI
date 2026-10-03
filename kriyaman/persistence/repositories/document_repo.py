from typing import Any, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.models import DocumentModel


class DocumentRepository:
    """Repository for managing ingested documents."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, document_id: str) -> DocumentModel | None:
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        )
        return result.scalars().first()

    async def get_by_id_and_user(self, document_id: str, user_id: str) -> DocumentModel | None:
        result = await self.session.execute(
            select(DocumentModel)
            .where(DocumentModel.id == document_id)
            .where(DocumentModel.user_id == user_id)
        )
        return result.scalars().first()

    async def get_by_session_and_hash(
        self, session_id: str, sha256_hash: str, user_id: str | None = None
    ) -> DocumentModel | None:
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.session_id == session_id)
            .where(DocumentModel.sha256 == sha256_hash)
        )
        if user_id:
            stmt = stmt.where(DocumentModel.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_session(
        self, session_id: str, limit: int = 50, offset: int = 0, user_id: str | None = None
    ) -> Sequence[DocumentModel]:
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.session_id == session_id)
        )
        if user_id:
            stmt = stmt.where(DocumentModel.user_id == user_id)
        stmt = stmt.order_by(DocumentModel.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> Sequence[DocumentModel]:
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.user_id == user_id)
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        session_id: str,
        name: str,
        mime_type: str,
        sha256: str,
        status: str = "processed",
        metadata: dict[str, Any] | None = None,
        document_id: str | None = None,
        user_id: str | None = None,
    ) -> DocumentModel:
        kwargs: dict[str, Any] = {
            "session_id": session_id,
            "name": name,
            "mime_type": mime_type,
            "sha256": sha256,
            "status": status,
            "metadata_json": metadata or {},
            "user_id": user_id,
        }
        if document_id:
            kwargs["id"] = document_id
        doc = DocumentModel(**kwargs)
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def delete(self, document_id: str) -> bool:
        doc = await self.get_by_id(document_id)
        if doc:
            await self.session.delete(doc)
            await self.session.flush()
            return True
        return False

    async def delete_for_user(self, document_id: str, user_id: str) -> bool:
        doc = await self.get_by_id_and_user(document_id, user_id)
        if doc:
            await self.session.delete(doc)
            await self.session.flush()
            return True
        return False

