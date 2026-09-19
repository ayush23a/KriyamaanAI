import time
from typing import Any, TypeVar
from google import genai
from google.genai import types
from domain.errors import ProviderError
from domain.models import CallBudget, ChatMessage, ProviderResult, UsageSnapshot
from domain.ports.llm import LLMCallRole, LLMProvider

T = TypeVar("T")


class GoogleGeminiAdapter(LLMProvider):
    """Google Gemini LLM adapter implementing LLMProvider via google-genai SDK."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.0,
        timeout_seconds: float = 30.0,
        client: genai.Client | None = None,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self._client = client or (genai.Client(api_key=api_key) if api_key else None)

    def _format_messages_to_prompt(self, messages: list[ChatMessage]) -> str:
        parts = []
        for msg in messages:
            role_label = msg.role.upper()
            parts.append(f"[{role_label}]:\n{msg.content}")
        return "\n\n".join(parts)

    def generate_text(
        self,
        messages: list[ChatMessage],
        budget: CallBudget,
        role: LLMCallRole = LLMCallRole.GENERATOR,
    ) -> ProviderResult[str]:
        if self._client is None:
            raise ProviderError("Google Gemini client is not configured with an API key.", provider_name="google_gemini")

        prompt = self._format_messages_to_prompt(messages)
        start_time = time.time()

        try:
            config = types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=budget.max_tokens,
            )
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage if present
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0

            usage = UsageSnapshot(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )

            return ProviderResult(
                data=response.text or "",
                usage=usage,
            )
        except Exception as exc:
            raise ProviderError(
                f"Gemini generate_text failed: {exc}",
                provider_name="google_gemini",
                is_transient=True,
            ) from exc

    def generate_structured(
        self,
        messages: list[ChatMessage],
        schema: type[T],
        budget: CallBudget,
        role: LLMCallRole = LLMCallRole.GENERATOR,
    ) -> ProviderResult[T]:
        if self._client is None:
            raise ProviderError("Google Gemini client is not configured with an API key.", provider_name="google_gemini")

        prompt = self._format_messages_to_prompt(messages)
        start_time = time.time()

        try:
            config = types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=budget.max_tokens,
                response_mime_type="application/json",
                response_schema=schema,
            )
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0

            usage = UsageSnapshot(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )

            parsed_data = schema.model_validate_json(response.text)  # type: ignore

            return ProviderResult(
                data=parsed_data,
                usage=usage,
            )
        except Exception as exc:
            raise ProviderError(
                f"Gemini generate_structured failed for {schema.__name__}: {exc}",
                provider_name="google_gemini",
                is_transient=True,
            ) from exc
