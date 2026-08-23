from __future__ import annotations

from dataclasses import dataclass, field

from app.meta import MetaClient
from app.models import KommoResult, LeadSubmission
from app.security import PayloadCipher
from app.service import LeadService
from app.storage import Storage


@dataclass
class FakeKommo:
    created: int = 0
    tasks: list[int] = field(default_factory=list)
    notes: list[int] = field(default_factory=list)
    chat_links: list[tuple[int, int]] = field(default_factory=list)

    async def reconcile_submission(self, submission_id: str):  # type: ignore[no-untyped-def]
        return None

    async def find_exact_contact(self, phone: str):  # type: ignore[no-untyped-def]
        return None

    async def create_incoming(self, submission, *, client_ip, existing_contact_id):  # type: ignore[no-untyped-def]
        self.created += 1
        return KommoResult(uid="uid-1", lead_id=1001, contact_id=2001)

    async def ensure_follow_up_task(self, lead_id: int, complete_till: int) -> None:
        self.tasks.append(lead_id)

    async def add_branch_note(self, lead_id: int, studio: str) -> None:
        self.notes.append(lead_id)

    async def link_chat_to_lead(self, source_lead_id: int, target_lead_id: int) -> None:
        self.chat_links.append((source_lead_id, target_lead_id))


@dataclass
class FakeMeta:
    events: list[dict] = field(default_factory=list)

    def build_event(self, submission, *, client_ip, client_user_agent):  # type: ignore[no-untyped-def]
        return MetaClient(dataset_id="1", access_token="x").build_event(
            submission,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
        )

    async def send_event(self, event: dict) -> str:
        self.events.append(event)
        return "trace"


async def test_service_saves_once_then_processes_outbox(
    settings, schema: dict, submission: LeadSubmission
) -> None:
    storage = Storage(settings.database_path)
    storage.initialize()
    kommo = FakeKommo()
    meta = FakeMeta()
    service = LeadService(
        settings=settings,
        schema=schema,
        storage=storage,
        cipher=PayloadCipher(settings.data_encryption_key.get_secret_value()),
        kommo=kommo,  # type: ignore[arg-type]
        meta=meta,  # type: ignore[arg-type]
    )

    first = await service.submit(
        submission,
        client_ip="203.0.113.10",
        client_user_agent="Test Browser",
    )
    second = await service.submit(
        submission,
        client_ip="203.0.113.10",
        client_user_agent="Test Browser",
    )
    assert first.kommo_saved and first.meta_queued
    assert second.duplicate
    assert kommo.created == 1

    assert await service.process_jobs_once() == 2
    assert len(meta.events) == 1
    assert meta.events[0]["event_id"] == submission.submission_id
    assert kommo.tasks == [1001]
    assert storage.health()["pending_jobs"] == 0

    assert service.queue_telegram_chat_link(submission.submission_id, 3001)
    assert not service.queue_telegram_chat_link(submission.submission_id, 3001)
    assert await service.process_jobs_once() == 1
    assert kommo.chat_links == [(3001, 1001)]
