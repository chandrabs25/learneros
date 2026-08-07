"""Provider-neutral model access built on the OpenAI-compatible SDK."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Literal, Sequence

from openai import OpenAI
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.config import settings
from app.observability import fingerprint, get_request_id, trace_event, trace_exception


LLMProvider = Literal["cerebras", "fireworks", "gemini"]
Message = dict[str, Any]
logger = logging.getLogger(__name__)
tracer = trace.get_tracer("learneros.llm")


class LLMConfigurationError(RuntimeError):
    """Raised when a requested provider has no configured credentials."""


@dataclass(frozen=True)
class ModelTarget:
    provider: LLMProvider
    model: str


def default_generation_targets() -> list[ModelTarget]:
    """Return the configured generation chain in priority order."""
    targets: list[ModelTarget] = []
    if settings.CEREBRAS_API_KEY:
        targets.append(ModelTarget("cerebras", settings.CEREBRAS_MODEL))
    if settings.FIREWORKS_API_KEY:
        targets.append(ModelTarget("fireworks", settings.FIREWORKS_MODEL))
    if not targets:
        # Preserve the useful FIREWORKS_API_KEY configuration error at call time.
        targets.append(ModelTarget("fireworks", settings.FIREWORKS_MODEL))
    return targets


def default_generation_target() -> ModelTarget:
    """Return the highest-priority configured generation target."""
    return default_generation_targets()[0]


def strip_code_fence(value: str) -> str:
    value = value.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines)
    return value.strip()


def parse_json_response(value: str) -> dict[str, Any]:
    parsed = json.loads(strip_code_fence(value))
    if not isinstance(parsed, dict):
        raise ValueError("Model response must be a JSON object")
    return parsed


def _text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") in {"text", "output_text"}:
                chunks.append(str(part.get("text") or ""))
            elif hasattr(part, "text"):
                chunks.append(str(part.text or ""))
        return "".join(chunks).strip()
    return str(content or "").strip()


class LLMService:
    """Shared clients, retries, safe telemetry, JSON parsing, and embeddings."""

    def __init__(self) -> None:
        self._clients: dict[tuple[LLMProvider, str], OpenAI] = {}

    def _provider_config(self, provider: LLMProvider, purpose: str) -> tuple[str, str]:
        if provider == "cerebras":
            api_key = settings.CEREBRAS_API_KEY
            base_url = settings.CEREBRAS_BASE_URL
        elif provider == "gemini":
            api_key = settings.GEMINI_API_KEY
            base_url = settings.GEMINI_OPENAI_BASE_URL
        else:
            api_key = (
                settings.FIREWORKS_API_KEY_EMBEDDINGS or settings.FIREWORKS_API_KEY
                if purpose == "embedding"
                else settings.FIREWORKS_API_KEY
            )
            base_url = settings.FIREWORKS_BASE_URL

        if not api_key:
            key_name = {
                "cerebras": "CEREBRAS_API_KEY",
                "gemini": "GEMINI_API_KEY",
                "fireworks": "FIREWORKS_API_KEY",
            }[provider]
            raise LLMConfigurationError(f"{key_name} not configured")
        return api_key, base_url

    def client(self, provider: LLMProvider, *, purpose: str = "generation") -> OpenAI:
        cache_key = (provider, purpose)
        client = self._clients.get(cache_key)
        if client is None:
            api_key, base_url = self._provider_config(provider, purpose)
            client = OpenAI(api_key=api_key, base_url=base_url)
            self._clients[cache_key] = client
        return client

    @staticmethod
    def _messages(
        *,
        prompt: str | None,
        system: str | None,
        messages: Sequence[Message] | None,
        images: Sequence[str] | None,
    ) -> list[Message]:
        if messages is not None:
            if images:
                raise ValueError("images cannot be combined with pre-built messages")
            return [dict(message) for message in messages]

        built: list[Message] = []
        if system:
            built.append({"role": "system", "content": system})

        if images:
            content: list[dict[str, Any]] = [{"type": "text", "text": prompt or ""}]
            for data_url in images:
                if not data_url.startswith("data:") or ";base64," not in data_url:
                    raise ValueError("image must be a base64 data URL")
                content.append({"type": "image_url", "image_url": {"url": data_url}})
            built.append({"role": "user", "content": content})
        else:
            built.append({"role": "user", "content": prompt or ""})
        return built

    def generate_text(
        self,
        *,
        provider: LLMProvider,
        model: str,
        prompt: str | None = None,
        system: str | None = None,
        messages: Sequence[Message] | None = None,
        images: Sequence[str] | None = None,
        temperature: float = 0.0,
        json_mode: bool = False,
        timeout: float = 60,
        operation: str = "generation",
        fallbacks: Sequence[ModelTarget] | None = None,
    ) -> str:
        request_messages = self._messages(
            prompt=prompt,
            system=system,
            messages=messages,
            images=images,
        )
        prompt_summary = json.dumps(request_messages, default=str, separators=(",", ":"))
        started = time.monotonic()

        with tracer.start_as_current_span(f"llm.{operation}") as span:
            span.set_attribute("gen_ai.system", provider)
            span.set_attribute("gen_ai.request.model", model)
            span.set_attribute("learneros.llm.operation", operation)
            span.set_attribute("learneros.prompt.fingerprint", fingerprint(prompt_summary))
            span.set_attribute("learneros.prompt.chars", len(prompt_summary))
            span.set_attribute("learneros.image.count", len(images or []))
            if get_request_id():
                span.set_attribute("learneros.request.id", get_request_id())
            trace_event(
                logger,
                "llm.request.started",
                operation=operation,
                provider=provider,
                model=model,
                prompt_fingerprint=fingerprint(prompt_summary),
                prompt_chars=len(prompt_summary),
                image_count=len(images or []),
            )
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": request_messages,
                    "temperature": temperature,
                    "timeout": timeout,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                response = self.client(provider).chat.completions.create(**kwargs)
                content = _text_content(response.choices[0].message.content)
                usage = getattr(response, "usage", None)
                if usage:
                    span.set_attribute("gen_ai.usage.input_tokens", int(usage.prompt_tokens or 0))
                    span.set_attribute("gen_ai.usage.output_tokens", int(usage.completion_tokens or 0))
                span.set_attribute("learneros.response.chars", len(content))
                span.set_attribute("learneros.response.fingerprint", fingerprint(content))
                trace_event(
                    logger,
                    "llm.response.received",
                    operation=operation,
                    provider=provider,
                    model=model,
                    latency_ms=round((time.monotonic() - started) * 1000, 2),
                    response_chars=len(content),
                    response_fingerprint=fingerprint(content),
                    prompt_tokens=getattr(usage, "prompt_tokens", None),
                    completion_tokens=getattr(usage, "completion_tokens", None),
                )
                return content
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)[:250]))
                remaining = list(fallbacks or [])
                if remaining:
                    fallback = remaining.pop(0)
                    trace_event(
                        logger,
                        "llm.provider.fallback",
                        operation=operation,
                        failed_provider=provider,
                        failed_model=model,
                        fallback_provider=fallback.provider,
                        fallback_model=fallback.model,
                        status_code=getattr(exc, "status_code", None),
                        error_type=type(exc).__name__,
                        latency_ms=round((time.monotonic() - started) * 1000, 2),
                    )
                    return self.generate_text(
                        provider=fallback.provider,
                        model=fallback.model,
                        prompt=prompt,
                        system=system,
                        messages=messages,
                        images=images,
                        temperature=temperature,
                        json_mode=json_mode,
                        timeout=timeout,
                        operation=operation,
                        fallbacks=remaining,
                    )
                trace_exception(
                    logger,
                    "llm.request.failed",
                    exc,
                    operation=operation,
                    provider=provider,
                    model=model,
                    latency_ms=round((time.monotonic() - started) * 1000, 2),
                )
                raise

    def generate_json(
        self,
        *,
        provider: LLMProvider,
        model: str,
        prompt: str,
        system: str = "Return only valid JSON matching the requested schema.",
        images: Sequence[str] | None = None,
        temperature: float = 0.0,
        timeout: float = 60,
        retries: int = 2,
        operation: str = "json_generation",
        fallbacks: Sequence[ModelTarget] | None = None,
    ) -> dict[str, Any]:
        if retries < 1:
            raise ValueError("retries must be at least 1")

        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                raw = self.generate_text(
                    provider=provider,
                    model=model,
                    prompt=prompt,
                    system=system,
                    images=images,
                    temperature=temperature,
                    json_mode=True,
                    timeout=timeout,
                    operation=operation,
                    fallbacks=fallbacks,
                )
                data = parse_json_response(raw)
                trace_event(
                    logger,
                    "llm.response.parsed",
                    operation=operation,
                    provider=provider,
                    model=model,
                    attempt=attempt,
                )
                return data
            except Exception as exc:
                last_error = exc
                trace_exception(
                    logger,
                    "llm.response.retry",
                    exc,
                    operation=operation,
                    provider=provider,
                    model=model,
                    attempt=attempt,
                    retries=retries,
                )
                if attempt == retries:
                    raise
        raise RuntimeError(f"LLM generation failed: {last_error}")

    def embed(
        self,
        *,
        provider: LLMProvider,
        model: str,
        text: str,
        retries: int = 2,
        operation: str = "embedding",
    ) -> list[float]:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Cannot embed empty text")

        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            started = time.monotonic()
            with tracer.start_as_current_span(f"llm.{operation}") as span:
                span.set_attribute("gen_ai.system", provider)
                span.set_attribute("gen_ai.request.model", model)
                span.set_attribute("learneros.input.fingerprint", fingerprint(clean_text))
                span.set_attribute("learneros.input.chars", len(clean_text))
                if get_request_id():
                    span.set_attribute("learneros.request.id", get_request_id())
                try:
                    response = self.client(provider, purpose="embedding").embeddings.create(
                        model=model,
                        input=clean_text,
                    )
                    vector = response.data[0].embedding if response.data else None
                    if not vector:
                        raise ValueError("Embedding provider returned an empty vector")
                    span.set_attribute("learneros.embedding.dimensions", len(vector))
                    trace_event(
                        logger,
                        "llm.embedding.completed",
                        operation=operation,
                        provider=provider,
                        model=model,
                        attempt=attempt,
                        dimensions=len(vector),
                        latency_ms=round((time.monotonic() - started) * 1000, 2),
                    )
                    return [float(value) for value in vector]
                except Exception as exc:
                    last_error = exc
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)[:250]))
                    if attempt == retries:
                        raise
        raise RuntimeError(f"Embedding generation failed: {last_error}")


llm_service = LLMService()
