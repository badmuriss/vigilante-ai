"""Structured logging + Prometheus metrics.

`configure_logging()` runs once at app startup. `metrics_router` exposes
/metrics for Prometheus scraping.
"""

from __future__ import annotations

import logging
import sys

import structlog
from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


def configure_logging(level: str = "INFO") -> None:
    """Configure stdlib + structlog to emit JSON lines."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# --- Prometheus metrics ---

stream_fps = Gauge(
    "vigilante_stream_fps",
    "Current FPS per camera",
    labelnames=["camera_id"],
)

inference_latency = Histogram(
    "vigilante_inference_latency_seconds",
    "Detector inference latency",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
)

alerts_total = Counter(
    "vigilante_alerts_total",
    "Total alerts generated",
    labelnames=["camera_id", "violation_type"],
)

stream_reconnects = Counter(
    "vigilante_stream_reconnects_total",
    "Total RTSP/webcam reconnects",
    labelnames=["camera_id"],
)

stream_online = Gauge(
    "vigilante_stream_online",
    "1 if the stream is currently producing frames, else 0",
    labelnames=["camera_id"],
)

whatsapp_messages_total = Counter(
    "vigilante_whatsapp_messages_total",
    "WhatsApp notifications attempted, labelled by outcome",
    labelnames=["tenant_id", "outcome"],  # outcome: sent | failed | skipped
)

teams_messages_total = Counter(
    "vigilante_teams_messages_total",
    "Microsoft Teams notifications attempted, labelled by outcome",
    labelnames=["tenant_id", "outcome"],  # outcome: sent | failed | skipped
)

# --- Conversational HUB metrics ---

chat_messages_total = Counter(
    "vigilante_chat_messages_total",
    "Chat messages processed by the agent",
    labelnames=["channel", "role"],  # channel: ui | whatsapp; role: user | assistant
)

chat_latency_seconds = Histogram(
    "vigilante_chat_latency_seconds",
    "Agent loop end-to-end latency",
    labelnames=["channel"],
    buckets=(0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0, 60.0),
)

chat_tool_calls_total = Counter(
    "vigilante_chat_tool_calls_total",
    "Tool invocations by the agent",
    labelnames=["tool", "status"],  # status: ok | error
)

kb_retrievals_total = Counter(
    "vigilante_kb_retrievals_total",
    "Knowledge-base hybrid retrievals executed",
)

kb_rerank_failures_total = Counter(
    "vigilante_kb_rerank_failures_total",
    "Reranker fallbacks (HF API unavailable or errored)",
)

llm_fallback_total = Counter(
    "vigilante_llm_fallback_total",
    "DeepSeek -> OpenRouter failovers",
)

wa_webhook_received_total = Counter(
    "vigilante_wa_webhook_received_total",
    "Inbound WhatsApp webhook deliveries",
    labelnames=["kind"],  # kind: text | audio | unsupported | unknown_tenant
)

wa_signature_failures_total = Counter(
    "vigilante_wa_signature_failures_total",
    "WhatsApp webhook HMAC signature mismatches",
)


metrics_router = APIRouter()


@metrics_router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
