from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .models import LeadSubmission
from .security import normalize_meta_name, normalize_meta_phone, sha256_hex


class MetaError(RuntimeError):
    pass


@dataclass(slots=True)
class MetaClient:
    dataset_id: str
    access_token: str
    api_version: str = "v25.0"
    test_event_code: str | None = None
    timeout_seconds: float = 8.0
    transport: httpx.AsyncBaseTransport | None = None

    def build_event(
        self,
        submission: LeadSubmission,
        *,
        client_ip: str,
        client_user_agent: str,
    ) -> dict[str, Any]:
        user_data: dict[str, Any] = {
            "ph": [sha256_hex(normalize_meta_phone(submission.phone))],
            "fn": [sha256_hex(normalize_meta_name(submission.name))],
            "client_ip_address": client_ip,
            "client_user_agent": client_user_agent,
        }
        if submission.fbp:
            user_data["fbp"] = submission.fbp
        if submission.fbc:
            user_data["fbc"] = submission.fbc

        return {
            "event_name": "Lead",
            "event_time": int(submission.submitted_at.timestamp()),
            "event_id": submission.submission_id,
            "event_source_url": submission.landing_url,
            "action_source": "website",
            "user_data": user_data,
        }

    async def send_event(self, event: dict[str, Any]) -> str:
        payload: dict[str, Any] = {"data": [event]}
        if self.test_event_code:
            payload["test_event_code"] = self.test_event_code
        async with httpx.AsyncClient(
            base_url="https://graph.facebook.com",
            timeout=self.timeout_seconds,
            transport=self.transport,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": "annaelle-landing-leads/1.0",
            },
        ) as client:
            response = await client.post(
                f"/{self.api_version}/{self.dataset_id}/events",
                json=payload,
            )
        if response.status_code >= 400:
            raise MetaError(f"META_HTTP_{response.status_code}")
        data = response.json()
        if int(data.get("events_received", 0)) != 1:
            raise MetaError("META_EVENT_NOT_ACCEPTED")
        return str(data.get("fbtrace_id", ""))
