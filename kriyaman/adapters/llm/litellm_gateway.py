import json
import logging
import os
import re
import time
from decimal import Decimal
from typing import Any, TypeVar

import litellm
from pydantic import ValidationError

from domain.errors import ProviderError
from domain.models import CallBudget, ChatMessage, ProviderResult, UsageSnapshot
from domain.ports.llm import LLMCallRole, LLMProvider

logger = logging.getLogger(__name__)

# Suppress debug output and telemetry from litellm in production
litellm.suppress_debug_info = True
litellm.telemetry = False

T = TypeVar("T")


def _extract_json_text(text: str) -> str:
    """Extracts raw JSON content from markdown code fences or surrounding text."""
    stripped = text.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
        if match:
            return match.group(1).strip()

    start_brace = stripped.find("{")
    end_brace = stripped.rfind("}")
    if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
        return stripped[start_brace : end_brace + 1]

    return stripped


class LiteLLMGatewayAdapter(LLMProvider):
    """LiteLLM-based multi-provider gateway supporting role-based routing,

    retries, fallback escalation, cost calculation, and secret sanitization.
    """

    def __init__(
        self,
        google_api_key: str = "",
        groq_api_key: str = "",
        planner_model: str = "groq/openai/gpt-oss-20b",
        judge_model: str = "groq/openai/gpt-oss-20b",
        generator_model: str = "gemini/gemini-3.6-flash",
        planner_fallback_models: list[str] | None = None,
        judge_fallback_models: list[str] | None = None,
        generator_fallback_models: list[str] | None = None,
        temperature: float = 0.0,
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
        retry_backoff: float = 1.0,
    ) -> None:
        self.google_api_key = google_api_key
        self.groq_api_key = groq_api_key
        self.planner_model = planner_model
        self.judge_model = judge_model
        self.generator_model = generator_model
        self.planner_fallback_models = planner_fallback_models or [
            "groq/openai/gpt-oss-120b",
            "gemini/gemini-3.6-flash",
            "gemini/gemini-3.1-flash-lite",
        ]
        self.judge_fallback_models = judge_fallback_models or [
            "groq/openai/gpt-oss-120b",
            "gemini/gemini-3.6-flash",
            "gemini/gemini-3.1-flash-lite",
        ]
        self.generator_fallback_models = generator_fallback_models or [
            "groq/openai/gpt-oss-120b",
            "gemini/gemini-3.1-flash-lite",
        ]
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def _sanitize(self, message: str) -> str:
        secrets = [s for s in [self.google_api_key, self.groq_api_key] if s and len(s) > 4]
        for env_var in ["GROQ_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"]:
            val = os.environ.get(env_var)
            if val and len(val) > 4:
                secrets.append(val)
        sanitized = message
        for secret in secrets:
            sanitized = sanitized.replace(secret, "[REDACTED_SECRET]")
        return sanitized

    def _get_models_for_role(self, role: LLMCallRole) -> list[str]:
        if role == LLMCallRole.PLANNER:
            candidates = [self.planner_model] + self.planner_fallback_models
        elif role == LLMCallRole.JUDGE:
            candidates = [self.judge_model] + self.judge_fallback_models
        else:  # GENERATOR
            candidates = [self.generator_model] + self.generator_fallback_models

        ordered: list[str] = []
        for c in candidates:
            if c and c not in ordered:
                ordered.append(c)
        return ordered

    def _get_api_key_for_model(self, model: str) -> str | None:
        model_lower = model.lower()
        if "groq" in model_lower:
            return self.groq_api_key or os.environ.get("GROQ_API_KEY")
        if "gemini" in model_lower:
            return (
                self.google_api_key
                or os.environ.get("GOOGLE_API_KEY")
                or os.environ.get("GEMINI_API_KEY")
            )
        return self.google_api_key or self.groq_api_key or None

    def _calculate_usage(
        self,
        response: Any,
        latency_ms: int,
    ) -> UsageSnapshot:
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

        cost_usd = Decimal("0.0")
        try:
            cost = litellm.completion_cost(completion_response=response)
            if cost is not None:
                cost_usd = Decimal(str(round(cost, 6)))
        except Exception:
            pass

        return UsageSnapshot(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=cost_usd,
        )

    def generate_text(
        self,
        messages: list[ChatMessage],
        budget: CallBudget,
        role: LLMCallRole = LLMCallRole.GENERATOR,
    ) -> ProviderResult[str]:
        models = self._get_models_for_role(role)
        litellm_messages = [{"role": m.role, "content": m.content} for m in messages]
        timeout = budget.timeout_seconds if budget else self.timeout_seconds
        max_tokens = budget.max_tokens if budget else None

        last_exc: Exception | None = None

        for model in models:
            api_key = self._get_api_key_for_model(model)
            if not api_key:
                logger.debug("Skipping model %s: no API key configured", model)
                last_exc = ProviderError(
                    f"No API key configured for model {model}",
                    provider_name="litellm_gateway",
                )
                continue

            for attempt in range(1 + self.max_retries):
                start_time = time.time()
                try:
                    kwargs: dict[str, Any] = {
                        "model": model,
                        "messages": litellm_messages,
                        "temperature": self.temperature,
                        "timeout": timeout,
                        "api_key": api_key,
                    }
                    if max_tokens:
                        kwargs["max_tokens"] = max_tokens

                    response = litellm.completion(**kwargs)
                    latency_ms = int((time.time() - start_time) * 1000)

                    content = ""
                    if response.choices and len(response.choices) > 0:
                        content = response.choices[0].message.content or ""

                    usage = self._calculate_usage(response, latency_ms)
                    return ProviderResult(
                        data=content,
                        usage=usage,
                        metadata={"model": model, "role": role.value},
                    )
                except Exception as exc:
                    last_exc = exc
                    sanitized_msg = self._sanitize(str(exc))
                    logger.warning(
                        "LiteLLM call failed (model=%s, attempt=%d/%d): %s",
                        model,
                        attempt + 1,
                        1 + self.max_retries,
                        sanitized_msg,
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.retry_backoff * (2**attempt))
                    else:
                        break  # Escalate to next model

        raise ProviderError(
            self._sanitize(
                f"LiteLLM text generation failed for role {role.value} across all candidate models. "
                f"Last error: {last_exc}"
            ),
            provider_name="litellm_gateway",
            is_transient=True,
        )

    def generate_structured(
        self,
        messages: list[ChatMessage],
        schema: type[T],
        budget: CallBudget,
        role: LLMCallRole = LLMCallRole.GENERATOR,
    ) -> ProviderResult[T]:
        models = self._get_models_for_role(role)
        timeout = budget.timeout_seconds if budget else self.timeout_seconds
        max_tokens = budget.max_tokens if budget else None

        # Build schema instructions to append to prompt
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        instruction_message = ChatMessage(
            role="system",
            content=(
                f"CRITICAL: You must respond ONLY with a valid, raw JSON object adhering to this schema:\n"
                f"{schema_json}\n"
                "Do not include markdown code block syntax (```), explanations, or any other text."
            ),
        )
        combined_messages = [instruction_message] + messages
        litellm_messages = [{"role": m.role, "content": m.content} for m in combined_messages]

        last_exc: Exception | None = None

        for model in models:
            api_key = self._get_api_key_for_model(model)
            if not api_key:
                logger.debug("Skipping model %s: no API key configured", model)
                last_exc = ProviderError(
                    f"No API key configured for model {model}",
                    provider_name="litellm_gateway",
                )
                continue

            for attempt in range(1 + self.max_retries):
                start_time = time.time()
                try:
                    kwargs: dict[str, Any] = {
                        "model": model,
                        "messages": litellm_messages,
                        "temperature": self.temperature,
                        "timeout": timeout,
                        "api_key": api_key,
                        "response_format": {"type": "json_object"},
                    }
                    if max_tokens:
                        kwargs["max_tokens"] = max_tokens

                    try:
                        response = litellm.completion(**kwargs)
                    except Exception:
                        # Some providers do not support response_format={"type": "json_object"}, retry without it
                        kwargs.pop("response_format", None)
                        response = litellm.completion(**kwargs)

                    latency_ms = int((time.time() - start_time) * 1000)

                    content = ""
                    if response.choices and len(response.choices) > 0:
                        content = response.choices[0].message.content or ""

                    json_text = _extract_json_text(content)
                    parsed_data = schema.model_validate_json(json_text)

                    usage = self._calculate_usage(response, latency_ms)
                    return ProviderResult(
                        data=parsed_data,
                        usage=usage,
                        metadata={"model": model, "role": role.value},
                    )
                except ValidationError as v_exc:
                    last_exc = v_exc
                    logger.warning(
                        "Schema validation failed for model %s (schema=%s): %s",
                        model,
                        schema.__name__,
                        str(v_exc),
                    )
                    # Escalate to next model immediately on schema validation failure
                    break
                except Exception as exc:
                    last_exc = exc
                    sanitized_msg = self._sanitize(str(exc))
                    logger.warning(
                        "LiteLLM structured call failed (model=%s, attempt=%d/%d): %s",
                        model,
                        attempt + 1,
                        1 + self.max_retries,
                        sanitized_msg,
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.retry_backoff * (2**attempt))
                    else:
                        break  # Escalate to next model

        raise ProviderError(
            self._sanitize(
                f"LiteLLM structured generation failed for schema {schema.__name__} (role={role.value}) across all candidate models. "
                f"Last error: {last_exc}"
            ),
            provider_name="litellm_gateway",
            is_transient=True,
        )

