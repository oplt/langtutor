from __future__ import annotations

from fastapi import WebSocket

WS_AUTH_SUBPROTOCOL = "languageapp.jwt"


def ws_accept_subprotocol(ws: WebSocket) -> str | None:
    offered = _offered_subprotocols(ws)
    if WS_AUTH_SUBPROTOCOL in offered:
        return WS_AUTH_SUBPROTOCOL
    return None


def extract_ws_token(ws: WebSocket) -> str:
    offered = _offered_subprotocols(ws)
    for index, protocol in enumerate(offered):
        if protocol == WS_AUTH_SUBPROTOCOL and index + 1 < len(offered):
            return offered[index + 1].strip()
    return ws.query_params.get("token", "").strip()


def _offered_subprotocols(ws: WebSocket) -> list[str]:
    raw = ws.headers.get("sec-websocket-protocol", "")
    return [part.strip() for part in raw.split(",") if part.strip()]
