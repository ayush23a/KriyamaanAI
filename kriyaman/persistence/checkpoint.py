import random
from collections.abc import AsyncIterator, Iterator, Sequence
from datetime import datetime, timezone
from typing import Any
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    RunnableConfig,
    get_checkpoint_metadata,
)
from sqlalchemy import delete, desc, select
from sqlalchemy.orm import sessionmaker
from persistence.db import get_sync_session_factory
from persistence.models import (
    LangGraphBlobModel,
    LangGraphCheckpointModel,
    LangGraphWriteModel,
)


class PostgresCheckpointSaver(BaseCheckpointSaver):
    """PostgreSQL-backed durable checkpointer for LangGraph execution workflows."""

    def __init__(self, session_factory=None, serde=None):
        super().__init__(serde=serde)
        self._session_factory = session_factory or get_sync_session_factory()

    def get_next_version(self, current: str | None, channel: None) -> str:
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(current.split(".")[0])
        next_v = current_v + 1
        next_h = random.random()
        return f"{next_v:032}.{next_h:016}"

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")

        with self._session_factory() as session:
            stmt = (
                select(LangGraphCheckpointModel)
                .where(LangGraphCheckpointModel.thread_id == thread_id)
                .where(LangGraphCheckpointModel.checkpoint_ns == checkpoint_ns)
            )
            if checkpoint_id:
                stmt = stmt.where(LangGraphCheckpointModel.checkpoint_id == checkpoint_id)
            else:
                stmt = stmt.order_by(desc(LangGraphCheckpointModel.created_at), desc(LangGraphCheckpointModel.checkpoint_id)).limit(1)

            row = session.execute(stmt).scalars().first()
            if not row:
                return None

            # 1. Deserialize checkpoint & metadata
            checkpoint: Checkpoint = self.serde.loads_typed((row.type, row.checkpoint_data))
            metadata: CheckpointMetadata = self.serde.loads_typed((row.metadata_type, row.metadata_data))

            # 2. Reconstruct channel values from blobs
            channel_values: dict[str, Any] = {}
            for channel, version in checkpoint.get("channel_versions", {}).items():
                blob_stmt = (
                    select(LangGraphBlobModel)
                    .where(LangGraphBlobModel.thread_id == thread_id)
                    .where(LangGraphBlobModel.checkpoint_ns == checkpoint_ns)
                    .where(LangGraphBlobModel.channel == channel)
                    .where(LangGraphBlobModel.version == str(version))
                )
                blob_row = session.execute(blob_stmt).scalars().first()
                if blob_row:
                    if blob_row.type != "empty":
                        channel_values[channel] = self.serde.loads_typed((blob_row.type, blob_row.blob_data))

            checkpoint["channel_values"] = channel_values

            # 3. Load pending writes
            writes_stmt = (
                select(LangGraphWriteModel)
                .where(LangGraphWriteModel.thread_id == thread_id)
                .where(LangGraphWriteModel.checkpoint_ns == checkpoint_ns)
                .where(LangGraphWriteModel.checkpoint_id == row.checkpoint_id)
                .order_by(LangGraphWriteModel.idx.asc())
            )
            write_rows = session.execute(writes_stmt).scalars().all()
            pending_writes = [
                (w.task_id, w.channel, self.serde.loads_typed((w.type, w.value_data)))
                for w in write_rows
            ]

            parent_config = None
            if row.parent_checkpoint_id:
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row.parent_checkpoint_id,
                    }
                }

            final_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": row.checkpoint_id,
                }
            }

            return CheckpointTuple(
                config=final_config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
                pending_writes=pending_writes,
            )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if not config:
            return

        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        with self._session_factory() as session:
            stmt = (
                select(LangGraphCheckpointModel)
                .where(LangGraphCheckpointModel.thread_id == thread_id)
                .where(LangGraphCheckpointModel.checkpoint_ns == checkpoint_ns)
                .order_by(desc(LangGraphCheckpointModel.created_at))
            )
            if before:
                before_id = before["configurable"].get("checkpoint_id")
                if before_id:
                    stmt = stmt.where(LangGraphCheckpointModel.checkpoint_id < before_id)

            if limit:
                stmt = stmt.limit(limit)

            rows = session.execute(stmt).scalars().all()
            for r in rows:
                c_tuple = self.get_tuple({
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": r.checkpoint_id,
                    }
                })
                if c_tuple:
                    yield c_tuple

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")
        checkpoint_id = checkpoint["id"]

        c = checkpoint.copy()
        values: dict[str, Any] = c.pop("channel_values", {})

        c_type, c_data = self.serde.dumps_typed(c)
        meta_type, meta_data = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))

        with self._session_factory() as session:
            with session.begin():
                # 1. Upsert Blobs for new versions
                for channel, version in new_versions.items():
                    if channel in values:
                        b_type, b_data = self.serde.dumps_typed(values[channel])
                    else:
                        b_type, b_data = ("empty", b"")

                    existing_blob = session.execute(
                        select(LangGraphBlobModel)
                        .where(LangGraphBlobModel.thread_id == thread_id)
                        .where(LangGraphBlobModel.checkpoint_ns == checkpoint_ns)
                        .where(LangGraphBlobModel.channel == channel)
                        .where(LangGraphBlobModel.version == str(version))
                    ).scalars().first()

                    if existing_blob:
                        existing_blob.type = b_type
                        existing_blob.blob_data = b_data
                    else:
                        blob_obj = LangGraphBlobModel(
                            thread_id=thread_id,
                            checkpoint_ns=checkpoint_ns,
                            channel=channel,
                            version=str(version),
                            type=b_type,
                            blob_data=b_data,
                        )
                        session.add(blob_obj)

                # 2. Upsert Checkpoint row
                existing_cp = session.execute(
                    select(LangGraphCheckpointModel)
                    .where(LangGraphCheckpointModel.thread_id == thread_id)
                    .where(LangGraphCheckpointModel.checkpoint_ns == checkpoint_ns)
                    .where(LangGraphCheckpointModel.checkpoint_id == checkpoint_id)
                ).scalars().first()

                if existing_cp:
                    existing_cp.parent_checkpoint_id = parent_checkpoint_id
                    existing_cp.type = c_type
                    existing_cp.checkpoint_data = c_data
                    existing_cp.metadata_type = meta_type
                    existing_cp.metadata_data = meta_data
                else:
                    cp_obj = LangGraphCheckpointModel(
                        thread_id=thread_id,
                        checkpoint_ns=checkpoint_ns,
                        checkpoint_id=checkpoint_id,
                        parent_checkpoint_id=parent_checkpoint_id,
                        type=c_type,
                        checkpoint_data=c_data,
                        metadata_type=meta_type,
                        metadata_data=meta_data,
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(cp_obj)

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        with self._session_factory() as session:
            with session.begin():
                for idx, (channel, val) in enumerate(writes):
                    write_idx = WRITES_IDX_MAP.get(channel, idx)
                    v_type, v_data = self.serde.dumps_typed(val)

                    existing = session.execute(
                        select(LangGraphWriteModel)
                        .where(LangGraphWriteModel.thread_id == thread_id)
                        .where(LangGraphWriteModel.checkpoint_ns == checkpoint_ns)
                        .where(LangGraphWriteModel.checkpoint_id == checkpoint_id)
                        .where(LangGraphWriteModel.task_id == task_id)
                        .where(LangGraphWriteModel.idx == write_idx)
                    ).scalars().first()

                    if existing:
                        existing.channel = channel
                        existing.type = v_type
                        existing.value_data = v_data
                        existing.task_path = task_path
                    else:
                        write_obj = LangGraphWriteModel(
                            thread_id=thread_id,
                            checkpoint_ns=checkpoint_ns,
                            checkpoint_id=checkpoint_id,
                            task_id=task_id,
                            idx=write_idx,
                            channel=channel,
                            type=v_type,
                            value_data=v_data,
                            task_path=task_path,
                        )
                        session.add(write_obj)

    def delete_thread(self, thread_id: str) -> None:
        with self._session_factory() as session:
            with session.begin():
                session.execute(
                    delete(LangGraphCheckpointModel).where(LangGraphCheckpointModel.thread_id == thread_id)
                )
                session.execute(
                    delete(LangGraphBlobModel).where(LangGraphBlobModel.thread_id == thread_id)
                )
                session.execute(
                    delete(LangGraphWriteModel).where(LangGraphWriteModel.thread_id == thread_id)
                )

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self.get_tuple(config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        return self.put_writes(config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        return self.delete_thread(thread_id)

