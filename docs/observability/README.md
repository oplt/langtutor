# Observability

## Metrics

Prometheus-format metrics are exposed at `GET /metrics`.

Key series:

| Metric | Description |
|--------|-------------|
| `http_requests_total` | HTTP requests by method, path template, status |
| `http_request_errors_total` | 5xx responses |
| `http_request_duration_ms_*` | Latency histogram |
| `llm_calls_total` | LLM invocations by task, provider, model |
| `llm_input_tokens_total` / `llm_output_tokens_total` | Estimated token usage |
| `app_uptime_seconds` | Process uptime |

## Grafana

Import [`grafana-dashboard.json`](./grafana-dashboard.json) into Grafana:

1. Add a Prometheus data source pointing at your scrape target (e.g. `http://backend:8000/metrics`).
2. Dashboards → Import → upload JSON.
3. Adjust panel queries if your scrape interval differs.

## Traces

Set `OTEL_EXPORTER_OTLP_ENDPOINT` (e.g. `http://otel-collector:4318/v1/traces`) to export spans. OpenTelemetry packages are included in `backend/requirements.txt`.

## Health

- `GET /health` — liveness
- `GET /ready` — database, Redis, LLM profile probe

## Dead letter queues

Failed tutor persistence and chat memory writes are retried three times, then recorded in Redis lists:

- `dead_letter:tutor_turn_persistence`
- `dead_letter:chat_memory_persistence`

Inspect with `LRANGE dead_letter:tutor_turn_persistence 0 10`.
