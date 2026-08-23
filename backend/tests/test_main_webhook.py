from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlencode

import httpx

SUBMISSION_ID = "018f1234-5678-7abc-8def-0123456789ab"


class StubStorage:
    def health(self) -> dict[str, int]:
        return {"submissions": 0, "pending_jobs": 0, "dead_jobs": 0}


class StubService:
    def __init__(self) -> None:
        self.storage = StubStorage()
        self.links: list[tuple[str, int]] = []

    async def worker_loop(self, stop_event: asyncio.Event) -> None:
        await stop_event.wait()

    def queue_telegram_chat_link(self, submission_id: str, lead_id: int) -> bool:
        self.links.append((submission_id, lead_id))
        return True


async def test_webhook_requires_secret_and_queues_link(
    settings, monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv(
        "DATA_ENCRYPTION_KEY", settings.data_encryption_key.get_secret_value()
    )
    monkeypatch.setenv("DATA_HASH_KEY", settings.data_hash_key.get_secret_value())
    monkeypatch.setenv(
        "KOMMO_LONG_LIVED_TOKEN", settings.kommo_long_lived_token.get_secret_value()
    )
    monkeypatch.setenv(
        "KOMMO_WEBHOOK_SECRET", settings.kommo_webhook_secret.get_secret_value()
    )
    monkeypatch.setenv("META_WEBSITE_DATASET_ID", settings.meta_website_dataset_id)
    monkeypatch.setenv(
        "META_WEBSITE_ACCESS_TOKEN", settings.meta_website_access_token.get_secret_value()
    )
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "import.sqlite3"))
    monkeypatch.setenv("SCHEMA_PATH", str(settings.schema_path))

    from app.main import create_app

    service = StubService()
    app = create_app(settings, service=service)  # type: ignore[arg-type]
    body = urlencode(
        {
            "add[0][text]": f"Код заявки: {SUBMISSION_ID}\n#META_LANDING",
            "add[0][origin]": "telegram",
            "add[0][type]": "incoming",
            "add[0][entity_id]": "3001",
        }
    ).encode()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        rejected = await client.post(
            "/v1/kommo/webhooks/incoming-message/wrong-secret",
            content=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        accepted = await client.post(
            "/v1/kommo/webhooks/incoming-message/kommo-webhook-test-secret",
            content=body,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    assert rejected.status_code == 404
    assert accepted.status_code == 200
    assert accepted.json() == {"queued": 1}
    assert service.links == [(SUBMISSION_ID, 3001)]
