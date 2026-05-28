"""OpenAI Whisper transcription for inbound WhatsApp voice notes.

Returns a placeholder string when `OPENAI_API_KEY` is missing so the agent
still receives *something* and the flow doesn't crash in keyless dev.
"""

from __future__ import annotations

import httpx
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

_PLACEHOLDER = "[áudio recebido, mas transcrição indisponível]"


def transcribe(audio_bytes: bytes, *, mime_type: str = "audio/ogg") -> str:
    if not audio_bytes:
        return _PLACEHOLDER
    if not settings.OPENAI_API_KEY.strip():
        log.warning("whisper_disabled", reason="OPENAI_API_KEY missing")
        return _PLACEHOLDER

    ext = "ogg" if "ogg" in mime_type else mime_type.split("/")[-1]
    try:
        with httpx.Client(timeout=settings.LLM_HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{settings.OPENAI_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                files={"file": (f"audio.{ext}", audio_bytes, mime_type)},
                data={"model": settings.WHISPER_MODEL},
            )
            resp.raise_for_status()
            return resp.json().get("text", "").strip() or _PLACEHOLDER
    except Exception as exc:  # noqa: BLE001
        log.warning("whisper_failed", error=str(exc))
        return _PLACEHOLDER
