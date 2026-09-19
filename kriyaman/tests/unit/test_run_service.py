import pytest
from langgraph.checkpoint.memory import MemorySaver
from application.run_service import RunExecutionService
from persistence.checkpoint import PostgresCheckpointSaver


def test_run_execution_service_default_checkpointer():
    """Verify that default production RunExecutionService uses PostgresCheckpointSaver."""
    service = RunExecutionService()
    assert isinstance(service.checkpointer, PostgresCheckpointSaver)

    graph = service.build_graph()
    assert isinstance(graph.checkpointer, PostgresCheckpointSaver)
    assert not isinstance(graph.checkpointer, MemorySaver)


def test_run_execution_service_injected_checkpointer():
    """Verify that a custom checkpointer can be injected for testing, but default never falls back to MemorySaver."""
    custom_saver = MemorySaver()
    service = RunExecutionService(checkpointer=custom_saver)
    assert service.checkpointer is custom_saver

    graph = service.build_graph()
    assert graph.checkpointer is custom_saver


def test_no_memory_saver_import_in_application_runtime():
    """Verify statically that application/run_service.py does not import MemorySaver."""
    import inspect
    import application.run_service as mod

    source = inspect.getsource(mod)
    assert "MemorySaver" not in source, "application/run_service.py must not contain any MemorySaver reference"

