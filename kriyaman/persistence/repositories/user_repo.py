from datetime import datetime, timezone
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.models import MemoryPrincipalModel, UserModel, utc_now


class UserRepository:
    """Repository for managing application users and their identities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> UserModel | None:
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalars().first()

    async def get_by_auth_subject(
        self, auth_subject: str, auth_provider: str = "clerk"
    ) -> UserModel | None:
        result = await self.session.execute(
            select(UserModel)
            .where(UserModel.auth_subject == auth_subject)
            .where(UserModel.auth_provider == auth_provider)
        )
        return result.scalars().first()

    async def get_or_create_clerk_user(
        self,
        auth_subject: str,
        email: str | None = None,
        display_name: str | None = None,
    ) -> UserModel:
        """Idempotently resolve or create a user mapped to a Clerk identity."""
        user = await self.get_by_auth_subject(auth_subject=auth_subject, auth_provider="clerk")
        if user:
            user.last_seen_at = utc_now()
            if email and not user.email:
                user.email = email
            if display_name and not user.display_name:
                user.display_name = display_name
            await self.session.flush()
            return user

        user = UserModel(
            id=str(uuid.uuid4()),
            auth_provider="clerk",
            auth_subject=auth_subject,
            email=email,
            display_name=display_name,
            status="active",
            last_seen_at=utc_now(),
        )
        self.session.add(user)
        await self.session.flush()

        # Ensure a default user-scoped memory principal exists
        principal_key = f"user_{user.id}"
        prin_result = await self.session.execute(
            select(MemoryPrincipalModel).where(MemoryPrincipalModel.namespace_key == principal_key)
        )
        principal = prin_result.scalars().first()
        if not principal:
            principal = MemoryPrincipalModel(
                user_id=user.id,
                namespace_key=principal_key,
                kind="user",
                metadata_json={"auth_subject": auth_subject},
            )
            self.session.add(principal)
            await self.session.flush()

        return user
