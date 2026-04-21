from pathlib import Path

DEFAULT_STORAGE_PATH = Path.home() / ".stuntrpa" / "scenarios"

EPHEMERAL_QUERY_PARAMS = frozenset({
    "_", "__", "_t", "_ts", "timestamp", "ts", "time", "t",
    "cachebuster", "cache_buster", "bust", "rand", "random",
    "nonce", "request_id", "requestId",
    "correlation_id", "correlationId", "x-request-id",
    "trace_id", "traceId", "span_id", "spanId",
})

SNAPSHOT_DEBOUNCE_MS = 500
