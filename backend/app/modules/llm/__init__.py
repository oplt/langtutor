"""LLM provider-agnostic service layer.

Keep this package init side-effect free. Some schema modules import
``backend.app.modules.llm.base`` during application bootstrap; eager imports here
create circular dependencies with provider factory code.
"""

__all__: list[str] = []
