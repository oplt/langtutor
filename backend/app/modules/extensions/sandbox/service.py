from __future__ import annotations

import ast
from typing import Any

from backend.app.core.config import settings


ALLOWED_NODE_TYPES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
    ast.FloorDiv,
)


def _validate_safe_ast(node: ast.AST) -> None:
    if not isinstance(node, ALLOWED_NODE_TYPES):
        raise ValueError(f"Disallowed syntax: {type(node).__name__}")
    for child in ast.iter_child_nodes(node):
        _validate_safe_ast(child)


def run_sandbox_expression(expression: str) -> dict[str, Any]:
    if not settings.SANDBOX_ENABLED:
        return {
            "ok": False,
            "error": "Sandbox is disabled. Set SANDBOX_ENABLED=true to enable.",
        }

    expr = (expression or "").strip()
    if not expr:
        return {"ok": False, "error": "Expression is empty"}
    if len(expr) > 200:
        return {"ok": False, "error": "Expression too long (max 200 chars)"}

    try:
        tree = ast.parse(expr, mode="eval")
        _validate_safe_ast(tree.body)
        result = eval(compile(tree, "<sandbox>", "eval"), {"__builtins__": {}}, {})
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    return {"ok": True, "result": result, "expression": expr}
