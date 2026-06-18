from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from backend.app.modules.agent.core.stream import StreamEvent, StreamEventType


class StreamBus:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        self._closed = False

    async def emit(self, event: StreamEvent) -> None:
        if not self._closed:
            await self._queue.put(event)

    async def content(self, text: str, *, source: str = "", metadata: dict[str, Any] | None = None) -> None:
        await self.emit(
            StreamEvent(
                type=StreamEventType.CONTENT,
                source=source,
                content=text,
                metadata=metadata or {},
            )
        )

    async def error(self, message: str, *, source: str = "") -> None:
        await self.emit(StreamEvent(type=StreamEventType.ERROR, source=source, content=message))

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._queue.put(None)

    async def subscribe(self) -> AsyncIterator[StreamEvent]:
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield event
