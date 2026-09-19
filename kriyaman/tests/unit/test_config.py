from decimal import Decimal
from app.config import Settings


def test_config_defaults():
    s = Settings()
    assert s.app_env == "development"
    assert s.cache_enabled is True
    assert s.max_retrieval_iterations == 3
    assert s.max_tool_calls == 3
    assert s.max_latency_ms == 30_000
    assert s.max_estimated_cost_usd == Decimal("0.25")
    assert s.observability_enabled is False

    budgets = s.get_execution_budgets()
    assert budgets.max_retrieval_iterations == 3
    assert budgets.max_tool_calls == 3
    assert budgets.max_latency_ms == 30_000


def test_config_environment_overrides(monkeypatch):
    monkeypatch.setenv("MAX_RETRIEVAL_ITERATIONS", "5")
    monkeypatch.setenv("CACHE_ENABLED", "false")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    s = Settings()
    assert s.max_retrieval_iterations == 5
    assert s.cache_enabled is False
    assert s.log_level == "DEBUG"

