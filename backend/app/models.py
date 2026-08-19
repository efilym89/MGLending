from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SUBMISSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
PHONE_RE = re.compile(r"^\+998\d{9}$")


class LeadSubmission(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)
    phone: str
    studio: str = Field(min_length=1, max_length=100)
    offer: str = Field(default="", max_length=160)
    contact_method: Literal["Telegram", "WhatsApp", "Позвоните мне"]
    comment: str = Field(default="", max_length=300)
    website: str = Field(default="", max_length=200)
    consent: bool
    utm_source: str = Field(default="", max_length=255)
    utm_medium: str = Field(default="", max_length=255)
    utm_campaign: str = Field(default="", max_length=255)
    utm_content: str = Field(default="", max_length=255)
    utm_term: str = Field(default="", max_length=255)
    fbclid: str = Field(default="", max_length=512)
    fbp: str = Field(default="", max_length=255)
    fbc: str = Field(default="", max_length=512)
    campaign_id: str = Field(default="", max_length=128)
    adset_id: str = Field(default="", max_length=128)
    ad_id: str = Field(default="", max_length=128)
    placement: str = Field(default="", max_length=128)
    landing_url: str = Field(min_length=1, max_length=2048)
    page_referrer: str = Field(default="", max_length=2048)
    page_language: str = Field(default="ru", max_length=16)
    submission_id: str
    form_started_at: datetime
    submitted_at: datetime
    form_elapsed_ms: int = Field(default=0, ge=0, le=86_400_000)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not PHONE_RE.fullmatch(value):
            raise ValueError("Phone must be in +998XXXXXXXXX format")
        return value

    @field_validator("submission_id")
    @classmethod
    def validate_submission_id(cls, value: str) -> str:
        if not SUBMISSION_ID_RE.fullmatch(value):
            raise ValueError("Invalid submission_id")
        return value

    @field_validator("form_started_at", "submitted_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_consent_and_timing(self) -> LeadSubmission:
        if not self.consent:
            raise ValueError("Consent is required")
        now = datetime.now(UTC)
        if (self.submitted_at - now).total_seconds() > 300:
            raise ValueError("submitted_at is too far in the future")
        if (now - self.submitted_at).total_seconds() > 86_400:
            raise ValueError("submitted_at is too old")
        return self

    def landing_host(self) -> str:
        return (urlparse(self.landing_url).hostname or "").lower()


class SubmitResponse(BaseModel):
    accepted: bool = True
    submission_id: str
    kommo_saved: bool
    meta_queued: bool
    duplicate: bool = False


class KommoResult(BaseModel):
    uid: str
    lead_id: int
    contact_id: int | None = None
