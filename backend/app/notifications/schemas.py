"""Pydantic schemas for the notifications API."""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.services.whatsapp_notifier import is_e164


class WhatsAppConfigResponse(BaseModel):
    """Public-facing config. `access_token` is NEVER returned — only
    `has_token` so the UI can show "token configured" without exposing the
    secret."""

    enabled: bool
    phone_number_id: str | None
    has_token: bool
    template_name: str | None
    template_language: str
    recipients: list[str]
    include_image: bool


class WhatsAppConfigUpdateRequest(BaseModel):
    enabled: bool = False
    phone_number_id: str | None = Field(default=None, max_length=64)
    # When omitted (None), keep the previously-stored token. When empty
    # string, clear the token. Otherwise replace it with the new value.
    access_token: str | None = Field(default=None, max_length=4096)
    template_name: str | None = Field(default=None, max_length=128)
    template_language: str = Field(default="pt_BR", max_length=16)
    recipients: list[str] = Field(default_factory=list)
    include_image: bool = True

    @field_validator("recipients")
    @classmethod
    def _validate_recipients(cls, value: list[str]) -> list[str]:
        for v in value:
            if not is_e164(v):
                raise ValueError(
                    f"Recipient '{v}' is not a valid E.164 number "
                    "(expected '+' followed by 7-15 digits, no leading zero)"
                )
        # de-dupe while preserving order
        seen: set[str] = set()
        out: list[str] = []
        for v in value:
            if v not in seen:
                seen.add(v)
                out.append(v)
        return out


class WhatsAppTestRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=24)

    @field_validator("phone_number")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        if not is_e164(value):
            raise ValueError(
                "phone_number must be in E.164 format (e.g. +5511999999999)"
            )
        return value


class WhatsAppTestResponse(BaseModel):
    ok: bool
    message_id: str | None = None
    error: str | None = None


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


class TeamsConfigResponse(BaseModel):
    """Public-facing Teams config. The webhook URL is never returned."""

    enabled: bool
    has_webhook_url: bool
    channel_name: str | None
    notify_on_confirmed: bool


class TeamsConfigUpdateRequest(BaseModel):
    enabled: bool = False
    # None keeps the previous URL, "" clears it, otherwise replaces it.
    webhook_url: str | None = Field(default=None, max_length=4096)
    channel_name: str | None = Field(default=None, max_length=128)
    notify_on_confirmed: bool = True

    @field_validator("webhook_url")
    @classmethod
    def _validate_webhook_url(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        trimmed = value.strip()
        if not _is_https_url(trimmed):
            raise ValueError("webhook_url must be an HTTPS URL")
        return trimmed

    @field_validator("channel_name")
    @classmethod
    def _trim_channel_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = value.strip()
        return trimmed or None


class TeamsTestResponse(BaseModel):
    ok: bool
    status_code: int | None = None
    error: str | None = None
