from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from app.config import Settings
from app.models import LeadSubmission


@pytest.fixture
def schema() -> dict:
    path = Path(__file__).parents[1] / "config" / "landing-kommo.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "test.sqlite3",
        data_encryption_key=Fernet.generate_key().decode(),
        data_hash_key="test-hash-key-that-is-not-used-in-production",
        schema_path=Path(__file__).parents[1] / "config" / "landing-kommo.schema.json",
        kommo_long_lived_token="kommo-test-token",
        meta_website_dataset_id="2079040289653796",
        meta_website_access_token="meta-test-token",
    )


@pytest.fixture
def submission() -> LeadSubmission:
    now = datetime.now(UTC).replace(microsecond=0)
    return LeadSubmission(
        name="  Sevara  ",
        phone="+998901234567",
        studio="Шота Руставели 33/1",
        offer="Любые 3 зоны",
        contact_method="Telegram",
        comment="Позвонить вечером",
        website="",
        consent=True,
        utm_source="meta",
        utm_medium="paid_social",
        utm_campaign="summer",
        utm_content="creative-a",
        utm_term="broad",
        fbclid="fb-click-id",
        fbp="fb.1.1780000000.123456789",
        fbc="fb.1.1780000000.fb-click-id",
        campaign_id="111",
        adset_id="222",
        ad_id="333",
        placement="instagram_stories",
        landing_url="https://annaelle.uz/main?utm_source=meta",
        page_referrer="https://instagram.com/",
        page_language="ru",
        submission_id="018f1234-5678-7abc-8def-0123456789ab",
        form_started_at=now - timedelta(seconds=20),
        submitted_at=now,
        form_elapsed_ms=20_000,
    )
