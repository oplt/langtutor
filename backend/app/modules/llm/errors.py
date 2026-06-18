from __future__ import annotations


class LLMError(Exception):
    code = "LLM_REQUEST_FAILED"

    def __init__(self, message: str, *, detail: str = "") -> None:
        super().__init__(message)
        self.detail = detail


class LLMConfigError(LLMError):
    code = "LLM_CONFIG_ERROR"


class LLMNetworkError(LLMError):
    code = "LLM_NETWORK_ERROR"


class LLMProviderUnavailableError(LLMError):
    code = "LLM_PROVIDER_UNAVAILABLE"
