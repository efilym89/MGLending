from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from fastapi import HTTPException, status

from .config import Settings
from .kommo import AmbiguousContactError, KommoClient, KommoError
from .meta import MetaClient, MetaError
from .models import KommoResult, LeadSubmission, SubmitResponse
from .security import PayloadCipher, keyed_hash
from .storage import JobRecord, Storage

logger = logging.getLogger("annaelle.landing_leads")


class LeadService:
    def __init__(
        self,
        *,
        settings: Settings,
        schema: dict[str, Any],
        storage: Storage,
        cipher: PayloadCipher,
        kommo: KommoClient,
        meta: MetaClient,
    ) -> None:
        self.settings = settings
        self.schema = schema
        self.storage = storage
        self.cipher = cipher
        self.kommo = kommo
        self.meta = meta

    async def submit(
        self,
        submission: LeadSubmission,
        *,
        client_ip: str,
        client_user_agent: str,
    ) -> SubmitResponse:
        if submission.website:
            return SubmitResponse(
                submission_id=submission.submission_id,
                kommo_saved=False,
                meta_queued=False,
            )
        if submission.landing_host() not in self.settings.landing_host_set:
            raise HTTPException(status_code=400, detail="LANDING_HOST_NOT_ALLOWED")

        hash_key = self.settings.data_hash_key.get_secret_value()
        phone_hash = keyed_hash(submission.phone, hash_key)
        ip_hash = keyed_hash(client_ip, hash_key)
        existing = self.storage.get_submission(submission.submission_id)
        if existing and existing.state in {"kommo_saved", "completed"}:
            return SubmitResponse(
                submission_id=submission.submission_id,
                kommo_saved=True,
                meta_queued=True,
                duplicate=True,
            )
        if existing and existing.encrypted_payload:
            original = LeadSubmission.model_validate(
                self.cipher.decrypt(existing.encrypted_payload)
            )
            if original.model_dump(mode="json") != submission.model_dump(mode="json"):
                raise HTTPException(status_code=409, detail="SUBMISSION_PAYLOAD_MISMATCH")
            submission = original
        if existing is None:
            since = int(time.time()) - 3600
            if (
                self.storage.count_recent("phone_hash", phone_hash, since)
                >= self.settings.max_phone_submissions_per_hour
            ):
                raise HTTPException(status_code=429, detail="PHONE_RATE_LIMITED")
            if (
                self.storage.count_recent("ip_hash", ip_hash, since)
                >= self.settings.max_ip_submissions_per_hour
            ):
                raise HTTPException(status_code=429, detail="IP_RATE_LIMITED")
        encrypted = self.cipher.encrypt(submission.model_dump(mode="json"))
        created = self.storage.create_submission(
            submission.submission_id, encrypted, phone_hash, ip_hash
        )
        record = self.storage.get_submission(submission.submission_id)
        if not record:
            raise HTTPException(status_code=500, detail="SUBMISSION_STORAGE_FAILED")
        if not self.storage.claim_submission(submission.submission_id):
            raise HTTPException(status_code=409, detail="SUBMISSION_IN_PROGRESS")

        try:
            result = await self._save_to_kommo(
                submission, client_ip=client_ip, attempts=record.attempts
            )
        except AmbiguousContactError as exc:
            self.storage.mark_failed(submission.submission_id, exc.code)
            raise HTTPException(status_code=409, detail=exc.code) from exc
        except KommoError as exc:
            if exc.retryable:
                self.storage.mark_retryable(submission.submission_id, exc.code)
                code = status.HTTP_503_SERVICE_UNAVAILABLE
            else:
                self.storage.mark_failed(submission.submission_id, exc.code)
                code = status.HTTP_502_BAD_GATEWAY
            logger.warning(
                "kommo_save_failed submission_id=%s code=%s",
                submission.submission_id,
                exc.code,
            )
            raise HTTPException(status_code=code, detail=exc.code) from exc
        except httpx.RequestError as exc:
            self.storage.mark_retryable(submission.submission_id, "KOMMO_NETWORK_ERROR")
            raise HTTPException(status_code=503, detail="KOMMO_NETWORK_ERROR") from exc

        meta_event = self.meta.build_event(
            submission,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
        )
        jobs: list[tuple[str, bytes]] = [
            ("meta_lead", self.cipher.encrypt(meta_event)),
            (
                "follow_up_task",
                self.cipher.encrypt(
                    {
                        "lead_id": result.lead_id,
                        "complete_till": int(time.time()) + self.settings.task_delay_seconds,
                    }
                ),
            ),
        ]
        if self.schema["branch_enum_by_landing_value"].get(submission.studio) is None:
            jobs.append(
                (
                    "branch_note",
                    self.cipher.encrypt({"lead_id": result.lead_id, "studio": submission.studio}),
                )
            )
        self.storage.save_kommo_and_jobs(
            submission.submission_id,
            kommo_uid=result.uid,
            lead_id=result.lead_id,
            contact_id=result.contact_id,
            jobs=jobs,
        )
        logger.info(
            "lead_saved submission_id=%s lead_id=%s", submission.submission_id, result.lead_id
        )
        return SubmitResponse(
            submission_id=submission.submission_id,
            kommo_saved=True,
            meta_queued=True,
            duplicate=not created,
        )

    async def _save_to_kommo(
        self, submission: LeadSubmission, *, client_ip: str, attempts: int
    ) -> KommoResult:
        if attempts > 0:
            reconciled = await self.kommo.reconcile_submission(submission.submission_id)
            if reconciled:
                return reconciled
        contact_id = await self.kommo.find_exact_contact(submission.phone)
        return await self.kommo.create_incoming(
            submission,
            client_ip=client_ip,
            existing_contact_id=contact_id,
        )

    async def process_jobs_once(self) -> int:
        jobs = self.storage.claim_due_jobs()
        for job in jobs:
            await self._process_job(job)
        return len(jobs)

    def queue_telegram_chat_link(self, submission_id: str, source_lead_id: int) -> bool:
        record = self.storage.get_submission(submission_id)
        if not record or not record.lead_id:
            return False
        if source_lead_id == record.lead_id:
            return False
        payload = self.cipher.encrypt(
            {"source_lead_id": source_lead_id, "target_lead_id": record.lead_id}
        )
        return self.storage.enqueue_job(submission_id, "kommo_chat_link", payload)

    async def _process_job(self, job: JobRecord) -> None:
        try:
            payload = self.cipher.decrypt(job.encrypted_payload)
            if job.kind == "meta_lead":
                await self.meta.send_event(payload)
            elif job.kind == "follow_up_task":
                await self.kommo.ensure_follow_up_task(
                    int(payload["lead_id"]), int(payload["complete_till"])
                )
            elif job.kind == "branch_note":
                await self.kommo.add_branch_note(int(payload["lead_id"]), str(payload["studio"]))
            elif job.kind == "kommo_chat_link":
                await self.kommo.link_chat_to_lead(
                    int(payload["source_lead_id"]), int(payload["target_lead_id"])
                )
            else:
                raise RuntimeError("UNKNOWN_JOB_KIND")
        except (MetaError, KommoError, httpx.RequestError, RuntimeError, ValueError) as exc:
            code = str(exc)[:100] or type(exc).__name__
            self.storage.retry_job(job.id, job.attempts, code)
            logger.warning(
                "job_failed submission_id=%s kind=%s code=%s",
                job.submission_id,
                job.kind,
                code,
            )
            return
        self.storage.finish_job(job.id)
        logger.info("job_done submission_id=%s kind=%s", job.submission_id, job.kind)

    async def worker_loop(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            try:
                await self.process_jobs_once()
            except Exception:
                logger.exception("worker_iteration_failed")
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=self.settings.worker_interval_seconds
                )
            except TimeoutError:
                continue
