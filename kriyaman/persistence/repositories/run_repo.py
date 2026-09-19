from typing import Any, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.json_utils import to_json_serializable
from persistence.models import (
    RetrievalRecordModel,
    RunEventModel,
    RunModel,
    ToolCallModel,
)


class RunRepository:
    """Repository for managing application execution runs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, run_id: str) -> RunModel | None:
        result = await self.session.execute(
            select(RunModel).where(RunModel.id == run_id)
        )
        return result.scalars().first()

    async def create(
        self,
        session_id: str,
        budgets: dict[str, Any],
        run_id: str | None = None,
        status: str = "running",
    ) -> RunModel:
        kwargs: dict[str, Any] = {
            "session_id": session_id,
            "status": status,
            "budgets_json": to_json_serializable(budgets) or {},
            "usage_json": {},
        }
        if run_id:
            kwargs["id"] = run_id
        run = RunModel(**kwargs)
        self.session.add(run)
        await self.session.flush()
        return run

    async def update_terminal(
        self,
        run_id: str,
        status: str,
        final_decision: str | None = None,
        usage: dict[str, Any] | None = None,
    ) -> RunModel | None:
        run = await self.get_by_id(run_id)
        if run:
            run.status = status
            run.final_decision = final_decision
            if usage is not None:
                run.usage_json = to_json_serializable(usage) or {}
            await self.session.flush()
        return run


class RunEventRepository:
    """Repository for appending and streaming immutable run execution events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def append_event(
        self,
        run_id: str,
        sequence: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> RunEventModel:
        event = RunEventModel(
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            payload_json=to_json_serializable(payload) or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_by_run(self, run_id: str) -> Sequence[RunEventModel]:
        result = await self.session.execute(
            select(RunEventModel)
            .where(RunEventModel.run_id == run_id)
            .order_by(RunEventModel.sequence.asc())
        )
        return result.scalars().all()


class RetrievalRecordRepository:
    """Repository for auditing retrieval iterations and decisions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        run_id: str,
        iteration: int,
        method: str,
        query: str,
        filters: dict[str, Any] | None = None,
        results: list[dict[str, Any]] | None = None,
        latency_ms: int = 0,
    ) -> RetrievalRecordModel:
        record = RetrievalRecordModel(
            run_id=run_id,
            iteration=iteration,
            method=method,
            query=query,
            filters_json=to_json_serializable(filters) or {},
            results_json=to_json_serializable(results) or [],
            latency_ms=latency_ms,
        )
        self.session.add(record)
        await self.session.flush()
        return record


class ToolCallRepository:
    """Repository for auditing tool invocations and results."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        run_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any] | None = None,
        status: str = "success",
        latency_ms: int = 0,
    ) -> ToolCallModel:
        call = ToolCallModel(
            run_id=run_id,
            tool_name=tool_name,
            arguments_json=to_json_serializable(arguments) or {},
            result_json=to_json_serializable(result) if result is not None else None,
            status=status,
            latency_ms=latency_ms,
        )
        self.session.add(call)
        await self.session.flush()
        return call

