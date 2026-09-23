from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.models import ClientCreditModel


class ClientCreditRepository:
    """Repository for managing client credit limits and cumulative usage costs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, client_id: str, default_limit: float = 5.0) -> ClientCreditModel:
        result = await self.session.execute(
            select(ClientCreditModel).where(ClientCreditModel.client_id == client_id)
        )
        record = result.scalars().first()
        if not record:
            record = ClientCreditModel(
                client_id=client_id,
                key_mode="default",
                default_spent_usd=0.0,
                byok_spent_usd=0.0,
                credit_limit_usd=default_limit,
            )
            self.session.add(record)
            await self.session.flush()
        return record

    async def record_usage(
        self, client_id: str, cost_usd: float, is_byok: bool = False
    ) -> ClientCreditModel:
        record = await self.get_or_create(client_id)
        if is_byok:
            record.byok_spent_usd = round(record.byok_spent_usd + cost_usd, 6)
            record.key_mode = "byok"
        else:
            record.default_spent_usd = round(record.default_spent_usd + cost_usd, 6)
            record.key_mode = "default"
        record.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return record

    async def check_budget(self, client_id: str) -> tuple[bool, float, float]:
        """Returns (is_allowed, remaining_usd, spent_usd)."""
        record = await self.get_or_create(client_id)
        spent = record.default_spent_usd
        limit = record.credit_limit_usd
        remaining = max(0.0, round(limit - spent, 6))
        is_allowed = spent < limit
        return is_allowed, remaining, spent

