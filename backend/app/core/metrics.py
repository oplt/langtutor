from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class RouteMetrics:
    count: int = 0
    errors: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    buckets: dict[str, int] = field(default_factory=lambda: {label: 0 for label in BUCKET_LABELS})


@dataclass
class LLMMetrics:
    count: int = 0
    errors: int = 0
    total_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


BUCKETS_MS: tuple[float, ...] = (50, 100, 250, 500, 1000, 2500, 5000, float("inf"))
BUCKET_LABELS: tuple[str, ...] = ("50", "100", "250", "500", "1000", "2500", "5000", "+Inf")


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = time.time()
        self._routes: defaultdict[tuple[str, str, int], RouteMetrics] = defaultdict(RouteMetrics)
        self._llm: defaultdict[tuple[str, str, str], LLMMetrics] = defaultdict(LLMMetrics)

    def observe_request(self, *, method: str, path: str, status_code: int, duration_ms: float) -> None:
        key = (method.upper(), path, int(status_code))
        with self._lock:
            metric = self._routes[key]
            metric.count += 1
            metric.total_ms += duration_ms
            metric.max_ms = max(metric.max_ms, duration_ms)
            if status_code >= 500:
                metric.errors += 1
            for limit, label in zip(BUCKETS_MS, BUCKET_LABELS):
                if duration_ms <= limit:
                    metric.buckets[label] += 1

    def observe_llm_call(
        self,
        *,
        task: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float,
        success: bool,
    ) -> None:
        key = (task, provider, model)
        with self._lock:
            metric = self._llm[key]
            metric.count += 1
            metric.total_ms += duration_ms
            metric.input_tokens += max(input_tokens, 0)
            metric.output_tokens += max(output_tokens, 0)
            if not success:
                metric.errors += 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP app_uptime_seconds Process uptime in seconds.",
            "# TYPE app_uptime_seconds gauge",
            f"app_uptime_seconds {time.time() - self._started_at:.3f}",
            "# HELP http_requests_total Total HTTP requests.",
            "# TYPE http_requests_total counter",
            "# HELP http_request_errors_total Total HTTP 5xx requests.",
            "# TYPE http_request_errors_total counter",
            "# HELP http_request_duration_ms_sum Total request duration in ms.",
            "# TYPE http_request_duration_ms_sum counter",
            "# HELP http_request_duration_ms_max Max request duration in ms.",
            "# TYPE http_request_duration_ms_max gauge",
            "# HELP http_request_duration_ms_bucket Request duration histogram buckets in ms.",
            "# TYPE http_request_duration_ms_bucket histogram",
            "# HELP llm_calls_total Total LLM calls by task, provider, and model.",
            "# TYPE llm_calls_total counter",
            "# HELP llm_call_errors_total Failed LLM calls by task, provider, and model.",
            "# TYPE llm_call_errors_total counter",
            "# HELP llm_call_duration_ms_sum Total LLM call duration in ms.",
            "# TYPE llm_call_duration_ms_sum counter",
            "# HELP llm_input_tokens_total Estimated input tokens sent to LLMs.",
            "# TYPE llm_input_tokens_total counter",
            "# HELP llm_output_tokens_total Estimated output tokens received from LLMs.",
            "# TYPE llm_output_tokens_total counter",
        ]
        with self._lock:
            items = list(self._routes.items())
            llm_items = list(self._llm.items())
        for (method, path, status), metric in sorted(items):
            labels = f'method="{method}",path="{_escape_label(path)}",status="{status}"'
            lines.append(f"http_requests_total{{{labels}}} {metric.count}")
            lines.append(f"http_request_errors_total{{{labels}}} {metric.errors}")
            lines.append(f"http_request_duration_ms_sum{{{labels}}} {metric.total_ms:.3f}")
            lines.append(f"http_request_duration_ms_max{{{labels}}} {metric.max_ms:.3f}")
            cumulative = 0
            for label in BUCKET_LABELS:
                cumulative += metric.buckets[label]
                lines.append(f'http_request_duration_ms_bucket{{{labels},le="{label}"}} {cumulative}')
            lines.append(f"http_request_duration_ms_count{{{labels}}} {metric.count}")
        for (task, provider, model), metric in sorted(llm_items):
            labels = (
                f'task="{_escape_label(task)}",'
                f'provider="{_escape_label(provider)}",'
                f'model="{_escape_label(model)}"'
            )
            lines.append(f"llm_calls_total{{{labels}}} {metric.count}")
            lines.append(f"llm_call_errors_total{{{labels}}} {metric.errors}")
            lines.append(f"llm_call_duration_ms_sum{{{labels}}} {metric.total_ms:.3f}")
            lines.append(f"llm_input_tokens_total{{{labels}}} {metric.input_tokens}")
            lines.append(f"llm_output_tokens_total{{{labels}}} {metric.output_tokens}")
        return "\n".join(lines) + "\n"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


metrics_registry = MetricsRegistry()
