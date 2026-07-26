"""Pydantic schemas for the notifications API."""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.services.whatsapp_notifier import is_e164


class WhatsAppOperatorOut(BaseModel):
    """An operator (phone) that acts on behalf of the tenant over WhatsApp."""

    id: str
    phone: str
    name: str | None
    enabled: bool


class WhatsAppConfigResponse(BaseModel):
    """Public-facing config. Meta credentials are global (env) and never
    returned — `connected` tells the UI whether the platform number is set up.
    """

    enabled: bool
    include_image: bool
    connected: bool
    operators: list[WhatsAppOperatorOut] = Field(default_factory=list)


class WhatsAppConfigUpdateRequest(BaseModel):
    enabled: bool = False
    include_image: bool = True


class WhatsAppOperatorCreateRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    name: str | None = Field(default=None, max_length=120)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        value = value.strip()
        if not is_e164(value):
            raise ValueError(
                "phone must be in E.164 format (e.g. +5511999999999)"
            )
        return value

    @field_validator("name")
    @classmethod
    def _trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = value.strip()
        return trimmed or None


class WhatsAppOperatorUpdateRequest(BaseModel):
    enabled: bool | None = None
    name: str | None = Field(default=None, max_length=120)

    @field_validator("name")
    @classmethod
    def _trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()


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
