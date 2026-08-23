from __future__ import annotations

from pathlib import Path

from app.storage import Storage


def test_submission_and_jobs_are_idempotent(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "db.sqlite3")
    storage.initialize()
    assert storage.create_submission("submission-00000001", b"cipher", "phone", "ip")
    assert not storage.create_submission("submission-00000001", b"cipher", "phone", "ip")
    assert storage.claim_submission("submission-00000001")
    assert not storage.claim_submission("submission-00000001")
    storage.save_kommo_and_jobs(
        "submission-00000001",
        kommo_uid="uid",
        lead_id=10,
        contact_id=20,
        jobs=[("meta_lead", b"meta"), ("follow_up_task", b"task")],
    )
    storage.save_kommo_and_jobs(
        "submission-00000001",
        kommo_uid="uid",
        lead_id=10,
        contact_id=20,
        jobs=[("meta_lead", b"meta"), ("follow_up_task", b"task")],
    )
    jobs = storage.claim_due_jobs()
    assert {job.kind for job in jobs} == {"meta_lead", "follow_up_task"}
    assert storage.get_submission("submission-00000001").encrypted_payload is None
    assert storage.enqueue_job("submission-00000001", "kommo_chat_link", b"chat")
    assert not storage.enqueue_job("submission-00000001", "kommo_chat_link", b"chat")
