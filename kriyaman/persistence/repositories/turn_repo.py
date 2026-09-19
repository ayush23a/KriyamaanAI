from typing import Any, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.json_utils import to_json_serializable
from persistence.models import ConversationTurnModel


class ConversationTurnRepository:
    """Repository for storing and querying conversation turns."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        session_id: str,
        run_id: str,
        user_query: str,
        answer: dict[str, Any] | None = None,
        status: str = "completed",
    ) -> ConversationTurnModel:
        turn = ConversationTurnModel(
            session_id=session_id,
            run_id=run_id,
            user_query=user_query,
            answer_json=to_json_serializable(answer),
            status=status,
        )
        self.session.add(turn)
        await self.session.flush()
        return turn

    async def list_recent_turns(
        self, session_id: str, limit: int = 10
    ) -> Sequence[ConversationTurnModel]:
        result = await self.session.execute(
            select(ConversationTurnModel)
            .where(ConversationTurnModel.session_id == session_id)
            .order_by(ConversationTurnModel.created_at.desc())
            .limit(limit)
        )
        turns = list(result.scalars().all())
        turns.reverse()  # Return in chronological order
        return turns

