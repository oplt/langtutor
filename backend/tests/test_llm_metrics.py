from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
from backend.app.core.metrics import MetricsRegistry
from backend.app.modules.llm.base import (
    BaseLLMClient,
    LLMChatRequest,
    LLMChatResponse,
    LLMHealth,
    LLMMessage,
    LLMModel,
    LLMProviderConfig,
)
from backend.app.modules.llm.task_client import LLMTaskClient


class FakeLLMClient(BaseLLMClient):
    async def health_check(self) -> LLMHealth:
        return LLMHealth(ok=True, status="running", provider="ollama")

    async def list_models(self) -> list[LLMModel]:
        return [LLMModel(id="fake", name="fake", local=True)]

    async def chat(self, request: LLMChatRequest) -> LLMChatResponse:
        return LLMChatResponse(provider="ollama", model=request.model, content="antwoord")

    async def stream_chat(self, request: LLMChatRequest) -> AsyncIterator[str]:
        yield "ant"
        yield "woord"


class FailingLLMClient(FakeLLMClient):
    async def chat(self, request: LLMChatRequest) -> LLMChatResponse:
        raise RuntimeError("provider failed")


def _task_client(client: BaseLLMClient) -> LLMTaskClient:
    config = LLMProviderConfig(provider="ollama", api_base="http://localhost:11434", model="fake")
    return LLMTaskClient(task="tutor", client=client, config=config)


def test_llm_task_client_records_chat_metrics() -> None:
    async def _run() -> str:
        registry = MetricsRegistry()
        with patch("backend.app.modules.llm.task_client.metrics_registry", registry):
            response = await _task_client(FakeLLMClient(_task_client_config())).chat(
                LLMChatRequest(messages=[LLMMessage(role="user", content="Hoi")])
            )
        assert response.content == "antwoord"
        return registry.render_prometheus()

    rendered = asyncio.run(_run())

    assert 'llm_calls_total{task="tutor",provider="ollama",model="fake"} 1' in rendered
    assert 'llm_call_errors_total{task="tutor",provider="ollama",model="fake"} 0' in rendered
    assert 'llm_input_tokens_total{task="tutor",provider="ollama",model="fake"}' in rendered
    assert 'llm_output_tokens_total{task="tutor",provider="ollama",model="fake"}' in rendered


def test_llm_task_client_records_error_metrics() -> None:
    async def _run() -> str:
        registry = MetricsRegistry()
        with patch("backend.app.modules.llm.task_client.metrics_registry", registry):
            with pytest.raises(RuntimeError):
                await _task_client(FailingLLMClient(_task_client_config())).chat(
                    LLMChatRequest(messages=[LLMMessage(role="user", content="Hoi")])
                )
        return registry.render_prometheus()

    rendered = asyncio.run(_run())

    assert 'llm_calls_total{task="tutor",provider="ollama",model="fake"} 1' in rendered
    assert 'llm_call_errors_total{task="tutor",provider="ollama",model="fake"} 1' in rendered


def test_llm_task_client_records_stream_metrics() -> None:
    async def _run() -> str:
        registry = MetricsRegistry()
        with patch("backend.app.modules.llm.task_client.metrics_registry", registry):
            chunks = [
                chunk
                async for chunk in _task_client(FakeLLMClient(_task_client_config())).stream_chat(
                    LLMChatRequest(messages=[LLMMessage(role="user", content="Hoi")])
                )
            ]
        assert chunks == ["ant", "woord"]
        return registry.render_prometheus()

    rendered = asyncio.run(_run())

    assert 'llm_calls_total{task="tutor",provider="ollama",model="fake"} 1' in rendered
    assert 'llm_call_errors_total{task="tutor",provider="ollama",model="fake"} 0' in rendered


def _task_client_config() -> LLMProviderConfig:
    return LLMProviderConfig(provider="ollama", api_base="http://localhost:11434", model="fake")
