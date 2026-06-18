from __future__ import annotations

from types import SimpleNamespace

from backend.app.modules.auth.ws_tokens import (
    WS_AUTH_SUBPROTOCOL,
    extract_ws_token,
    ws_accept_subprotocol,
)


def test_extract_ws_token_from_subprotocol_header() -> None:
    ws = SimpleNamespace(
        headers={"sec-websocket-protocol": f"{WS_AUTH_SUBPROTOCOL}, jwt-token"},
        query_params={},
    )

    assert extract_ws_token(ws) == "jwt-token"
    assert ws_accept_subprotocol(ws) == WS_AUTH_SUBPROTOCOL


def test_extract_ws_token_keeps_query_fallback_for_existing_clients() -> None:
    ws = SimpleNamespace(headers={}, query_params={"token": "legacy-token"})

    assert extract_ws_token(ws) == "legacy-token"
    assert ws_accept_subprotocol(ws) is None
