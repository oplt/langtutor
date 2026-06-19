from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool
from backend.app.modules.agent.core.stream import LoopOutcome, StreamEvent, StreamEventType
from backend.app.modules.agent.core.stream_bus import StreamBus
from backend.app.modules.llm.base import LLMChatRequest, LLMMessage, LLMToolCall
from backend.app.modules.llm.task_client import LLMTaskClient

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 8
_MAX_ITERATION_FALLBACK = (
    "I hit the tool step limit for this turn. Please ask a shorter follow-up "
    "or rephrase your question."
)

READ_ONLY_TOOLS = frozenset(
    {
        "search_knowledge",
        "rag_search",
        "read_memory",
        "lookup_dictionary",
        "vision_ocr",
        "sandbox_eval",
    }
)


def _is_final_answer_turn(messages: list[LLMMessage]) -> bool:
    return bool(messages) and messages[-1].role == "tool"


_KNOWLEDGE_GROUNDING_HINTS = (
    "mean",
    "grammar",
    "conjug",
    "translate",
    "what is",
    "how do you",
    "dutch word",
    "betekent",
    "uitleg",
    "spell",
    "pronoun",
)


def _requires_knowledge_grounding(context: AgentContext) -> bool:
    message = (context.user_message or "").lower()
    if not message.strip():
        return False
    return any(hint in message for hint in _KNOWLEDGE_GROUNDING_HINTS)


def _record_tool_call(context: AgentContext, tool_name: str) -> None:
    called = context.metadata.setdefault("tools_called", [])
    if isinstance(called, list) and tool_name not in called:
        called.append(tool_name)


class AgentLoopRunner:
    def __init__(self, *, source: str = "chat") -> None:
        self.source = source

    async def run(
        self,
        *,
        context: AgentContext,
        bus: StreamBus,
        llm_client: LLMTaskClient,
        tools: list[BaseTool],
        system_prompt: str,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> LoopOutcome:
        resume_raw = context.metadata.get("resume_messages")
        if isinstance(resume_raw, list) and resume_raw:
            messages = [self._coerce_message(item) for item in resume_raw]
        else:
            messages = self._build_messages(context, system_prompt)
        tool_schemas = [tool.get_definition().to_openai_schema() for tool in tools]
        tool_map = {tool.name: tool for tool in tools}
        iterations = 0
        final_text = ""
        grounding_retries = 0

        for iteration in range(1, max_iterations + 1):
            iterations = iteration
            stream_final = bool(
                llm_client.config.streaming
                and (not tool_schemas or _is_final_answer_turn(messages))
            )
            request = LLMChatRequest(
                messages=messages,
                model=context.config_overrides.get("model", ""),
                temperature=context.config_overrides.get("temperature"),
                max_tokens=context.config_overrides.get("max_tokens"),
                tools=None if stream_final else (tool_schemas or None),
            )

            if stream_final:
                chunks: list[str] = []
                async for delta in llm_client.stream_chat(request):
                    chunks.append(delta)
                    await bus.emit(
                        StreamEvent(
                            type=StreamEventType.CONTENT_DELTA,
                            source=self.source,
                            content=delta,
                        )
                    )
                final_text = "".join(chunks).strip()
                if final_text:
                    return LoopOutcome(
                        final_text=final_text,
                        iterations=iterations,
                        completed=True,
                        messages=[message.model_dump() for message in messages],
                    )
                continue

            response = await llm_client.chat(request)

            if response.tool_calls:
                messages.append(
                    LLMMessage(
                        role="assistant",
                        content=response.content or "",
                        tool_calls=list(response.tool_calls),
                    )
                )
                pause_outcome = await self._execute_tool_calls(
                    calls=list(response.tool_calls),
                    tool_map=tool_map,
                    context=context,
                    bus=bus,
                    messages=messages,
                    iterations=iterations,
                )
                if pause_outcome is not None:
                    return pause_outcome
                continue

            final_text = (response.content or "").strip()
            if (
                final_text
                and _requires_knowledge_grounding(context)
                and grounding_retries < 1
            ):
                called = context.metadata.get("tools_called") or []
                if isinstance(called, list) and "search_knowledge" not in called:
                    grounding_retries += 1
                    messages.append(
                        LLMMessage(
                            role="system",
                            content=(
                                "Grounding required: call `search_knowledge` before answering "
                                "questions about Dutch meanings, grammar, or usage."
                            ),
                        )
                    )
                    continue
            if final_text:
                await bus.content(final_text, source=self.source)
            return LoopOutcome(
                final_text=final_text,
                iterations=iterations,
                completed=True,
                messages=[message.model_dump() for message in messages],
            )

        if final_text:
            await bus.content(final_text, source=self.source)
        if iterations >= max_iterations and not final_text:
            logger.warning(
                "agent_loop_max_iterations source=%s iterations=%s user_id=%s",
                self.source,
                iterations,
                context.user_id,
            )
            final_text = _MAX_ITERATION_FALLBACK
            await bus.content(final_text, source=self.source)
        return LoopOutcome(
            final_text=final_text,
            iterations=iterations,
            completed=bool(final_text),
            messages=[message.model_dump() for message in messages],
        )

    async def _dispatch_tool(
        self,
        call: LLMToolCall,
        tool_map: dict[str, BaseTool],
        context: AgentContext,
    ):
        tool = tool_map.get(call.name)
        if tool is None:
            from backend.app.modules.agent.core.protocols import ToolResult

            return ToolResult(content=f"Unknown tool: {call.name}")
        meta = context.metadata or {}
        logger.info(
            "agent_tool_call tool=%s trace_id=%s request_id=%s turn_id=%s user_id=%s",
            call.name,
            meta.get("trace_id"),
            meta.get("request_id"),
            meta.get("turn_id"),
            context.user_id,
        )
        result = await tool.execute(context, **call.arguments)
        _record_tool_call(context, call.name)
        return result

    async def _execute_tool_calls(
        self,
        *,
        calls: list[LLMToolCall],
        tool_map: dict[str, BaseTool],
        context: AgentContext,
        bus: StreamBus,
        messages: list[LLMMessage],
        iterations: int,
    ) -> LoopOutcome | None:
        parallel = len(calls) > 1 and all(call.name in READ_ONLY_TOOLS for call in calls)

        async def _run_one(call: LLMToolCall):
            await bus.emit(
                StreamEvent(
                    type=StreamEventType.TOOL_START,
                    source="agent_loop",
                    content=call.name,
                    metadata={"arguments": call.arguments},
                )
            )
            result = await self._dispatch_tool(call, tool_map, context)
            await bus.emit(
                StreamEvent(
                    type=StreamEventType.TOOL_END,
                    source="agent_loop",
                    content=result.content,
                    metadata=result.metadata,
                )
            )
            return call, result

        if parallel:
            pairs = list(await asyncio.gather(*[_run_one(call) for call in calls]))
        else:
            pairs = [await _run_one(call) for call in calls]

        for call, result in pairs:
            if result.pause_for_user:
                ask_user = result.metadata.get("ask_user")
                pending = {"id": call.id, "name": call.name}
                await bus.emit(
                    StreamEvent(
                        type=StreamEventType.ASK_USER,
                        source="ask_user",
                        content=result.pause_question,
                        metadata={
                            "agent_messages": [message.model_dump() for message in messages],
                            "pending_tool_call": pending,
                            "ask_user": ask_user,
                        },
                    )
                )
                return LoopOutcome(
                    final_text=result.pause_question,
                    iterations=iterations,
                    paused=True,
                    pause_question=result.pause_question,
                    messages=[message.model_dump() for message in messages],
                    pending_tool_call=pending,
                    ask_user=ask_user if isinstance(ask_user, dict) else None,
                )
            messages.append(
                LLMMessage(
                    role="tool",
                    content=result.content,
                    tool_call_id=call.id,
                    name=call.name,
                )
            )
        return None

    def _build_messages(self, context: AgentContext, system_prompt: str) -> list[LLMMessage]:
        messages: list[LLMMessage] = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        history = context.conversation_history
        if len(history) > 12:
            history = history[-12:]
        for item in history:
            messages.append(self._coerce_message(item))
        if context.user_message:
            messages.append(LLMMessage(role="user", content=context.user_message))
        return messages

    def _coerce_message(self, item: dict[str, Any]) -> LLMMessage:
        role = item.get("role")
        content = item.get("content")
        tool_calls_raw = item.get("tool_calls")
        tool_calls: list[LLMToolCall] | None = None
        if isinstance(tool_calls_raw, list) and tool_calls_raw:
            tool_calls = [LLMToolCall.model_validate(call) for call in tool_calls_raw]
        return LLMMessage(
            role=role,
            content=str(content or ""),
            tool_call_id=item.get("tool_call_id"),
            name=item.get("name"),
            tool_calls=tool_calls,
        )
