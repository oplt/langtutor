from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from urllib import error, request


async def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout_seconds: float = 60.0,
) -> tuple[int, dict[str, Any] | list[Any] | str]:
    payload = None
    req_headers = dict(headers or {})
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    def _call() -> tuple[int, dict[str, Any] | list[Any] | str]:
        req = request.Request(url, data=payload, headers=req_headers, method=method.upper())
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                status = response.status
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            status = exc.code
        if not raw:
            return status, {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return status, raw
        return status, parsed

    return await asyncio.to_thread(_call)


async def stream_post_lines(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout_seconds: float = 60.0,
) -> AsyncIterator[str]:
    payload = json.dumps(body or {}).encode("utf-8")
    req_headers = dict(headers or {})
    req_headers.setdefault("Content-Type", "application/json")
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _worker() -> None:
        try:
            req = request.Request(url, data=payload, headers=req_headers, method="POST")
            with request.urlopen(req, timeout=timeout_seconds) as response:
                while True:
                    line = response.readline()
                    if not line:
                        break
                    asyncio.run_coroutine_threadsafe(
                        queue.put(line.decode("utf-8", errors="replace").rstrip("\r\n")),
                        loop,
                    ).result()
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(queue.put(f"__stream_error__:{exc}"), loop).result()
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

    loop.run_in_executor(None, _worker)

    while True:
        item = await queue.get()
        if item is None:
            break
        if item.startswith("__stream_error__:"):
            raise RuntimeError(item.split(":", 1)[1])
        if item:
            yield item
