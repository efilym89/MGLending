from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .models import KommoResult, LeadSubmission


class KommoError(RuntimeError):
    def __init__(self, code: str, *, retryable: bool, unknown_outcome: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.unknown_outcome = unknown_outcome


class AmbiguousContactError(KommoError):
    def __init__(self) -> None:
        super().__init__("KOMMO_CONTACT_AMBIGUOUS", retryable=False)


@dataclass(slots=True)
class KommoClient:
    domain: str
    token: str
    schema: dict[str, Any]
    timeout_seconds: float = 8.0
    transport: httpx.AsyncBaseTransport | None = None

    async def find_exact_contact(self, phone: str) -> int | None:
        response = await self._request(
            "GET",
            "/api/v4/contacts",
            params={"query": phone, "limit": 50},
            retry_writes=False,
        )
        if response.status_code == 204:
            return None
        contacts = response.json().get("_embedded", {}).get("contacts", [])
        exact_ids = [
            int(contact["id"])
            for contact in contacts
            if self._contact_has_exact_phone(contact, phone)
        ]
        exact_ids = list(dict.fromkeys(exact_ids))
        if len(exact_ids) > 1:
            raise AmbiguousContactError()
        return exact_ids[0] if exact_ids else None

    async def reconcile_submission(self, submission_id: str) -> KommoResult | None:
        field_id = int(self.schema["lead_fields"]["submission_id"]["id"])
        response = await self._request(
            "GET",
            "/api/v4/leads",
            params={"query": submission_id, "limit": 50},
            retry_writes=False,
        )
        if response.status_code == 204:
            return None
        matches = []
        for lead in response.json().get("_embedded", {}).get("leads", []):
            for field in lead.get("custom_fields_values") or []:
                if int(field.get("field_id", 0)) != field_id:
                    continue
                if any(
                    str(item.get("value", "")) == submission_id
                    for item in field.get("values") or []
                ):
                    matches.append(lead)
        if len(matches) > 1:
            raise KommoError("KOMMO_SUBMISSION_AMBIGUOUS", retryable=False)
        if not matches:
            return None
        return KommoResult(uid=f"reconciled:{submission_id}", lead_id=int(matches[0]["id"]))

    async def create_incoming(
        self,
        submission: LeadSubmission,
        *,
        client_ip: str,
        existing_contact_id: int | None,
    ) -> KommoResult:
        payload = self.build_incoming_payload(
            submission,
            client_ip=client_ip,
            existing_contact_id=existing_contact_id,
        )
        try:
            response = await self._request(
                "POST",
                "/api/v4/leads/unsorted/forms",
                json=[payload],
                retry_writes=False,
            )
        except (httpx.ReadTimeout, httpx.WriteError, httpx.RemoteProtocolError) as exc:
            raise KommoError(
                "KOMMO_POST_OUTCOME_UNKNOWN", retryable=True, unknown_outcome=True
            ) from exc
        item_list = response.json().get("_embedded", {}).get("unsorted", [])
        if len(item_list) != 1:
            raise KommoError("KOMMO_INVALID_CREATE_RESPONSE", retryable=True)
        item = item_list[0]
        leads = item.get("_embedded", {}).get("leads", [])
        contacts = item.get("_embedded", {}).get("contacts", [])
        if len(leads) != 1 or not item.get("uid"):
            raise KommoError("KOMMO_INVALID_CREATE_RESPONSE", retryable=True)
        return KommoResult(
            uid=str(item["uid"]),
            lead_id=int(leads[0]["id"]),
            contact_id=int(contacts[0]["id"]) if contacts else existing_contact_id,
        )

    def build_incoming_payload(
        self,
        submission: LeadSubmission,
        *,
        client_ip: str,
        existing_contact_id: int | None,
    ) -> dict[str, Any]:
        lead_fields = self.schema["lead_fields"]
        tracking_fields = self.schema["tracking_fields_by_code"]
        fields: list[dict[str, Any]] = []

        def add(field_id: int, value: str | int, **extra: Any) -> None:
            if value != "":
                fields.append({"field_id": int(field_id), "values": [{"value": value, **extra}]})

        add(lead_fields["submission_id"]["id"], submission.submission_id)
        add(lead_fields["landing_url"]["id"], submission.landing_url)
        branch_enum = self.schema["branch_enum_by_landing_value"].get(submission.studio)
        comment = submission.comment
        if branch_enum is None and submission.studio:
            comment = f"{comment}\nФилиал из формы: {submission.studio}".strip()
        add(lead_fields["comment"]["id"], comment)
        add(lead_fields["campaign_id"]["id"], submission.campaign_id)
        add(lead_fields["adset_id"]["id"], submission.adset_id)
        add(lead_fields["ad_id"]["id"], submission.ad_id)
        add(lead_fields["placement"]["id"], submission.placement)
        add(lead_fields["fbp"]["id"], submission.fbp)
        add(lead_fields["fbc"]["id"], submission.fbc)
        add(lead_fields["offer"]["id"], submission.offer)
        add(lead_fields["contact_method"]["id"], submission.contact_method)
        if branch_enum is not None:
            fields.append(
                {
                    "field_id": int(lead_fields["branch"]["id"]),
                    "values": [{"enum_id": int(branch_enum)}],
                }
            )
        tracking_values = {
            "UTM_SOURCE": submission.utm_source,
            "UTM_MEDIUM": submission.utm_medium,
            "UTM_CAMPAIGN": submission.utm_campaign,
            "UTM_CONTENT": submission.utm_content,
            "UTM_TERM": submission.utm_term,
            "REFERRER": submission.page_referrer,
            "FBCLID": submission.fbclid,
        }
        for code, value in tracking_values.items():
            add(tracking_fields[code], value)

        if existing_contact_id is not None:
            contact: dict[str, Any] = {"id": existing_contact_id}
        else:
            contact = {
                "name": submission.name,
                "custom_fields_values": [
                    {
                        "field_code": "PHONE",
                        "values": [{"value": submission.phone, "enum_code": "WORK"}],
                    }
                ],
            }
        lead = {
            "name": f"Лендинг — {submission.name}",
            "created_by": 0,
            "custom_fields_values": fields,
            "_embedded": {"tags": [{"id": int(self.schema["kommo"]["tag"]["id"])}]},
        }
        sent_at = int(submission.submitted_at.timestamp())
        return {
            "request_id": submission.submission_id,
            "source_uid": self.schema["source"]["source_uid"],
            "source_name": self.schema["source"]["source_name"],
            "pipeline_id": int(self.schema["kommo"]["pipeline_id"]),
            "created_at": sent_at,
            "_embedded": {"leads": [lead], "contacts": [contact]},
            "metadata": {
                "ip": client_ip,
                "form_id": self.schema["source"]["form_id"],
                "form_sent_at": sent_at,
                "form_name": self.schema["source"]["form_name"],
                "form_page": submission.landing_url,
                "referer": submission.page_referrer or submission.landing_url,
            },
        }

    async def ensure_follow_up_task(self, lead_id: int, complete_till: int) -> None:
        text = "Обработать новую заявку с лендинга Annaelle"
        response = await self._request(
            "GET",
            "/api/v4/tasks",
            params={"filter[entity_id]": lead_id, "filter[entity_type]": "leads", "limit": 50},
            retry_writes=False,
        )
        if response.status_code != 204:
            tasks = response.json().get("_embedded", {}).get("tasks", [])
            if any(not task.get("is_completed") and task.get("text") == text for task in tasks):
                return
        await self._request(
            "POST",
            "/api/v4/tasks",
            json=[
                {
                    "task_type_id": int(self.schema["kommo"]["follow_up_task_type_id"]),
                    "text": text,
                    "complete_till": complete_till,
                    "entity_id": lead_id,
                    "entity_type": "leads",
                }
            ],
            retry_writes=False,
        )

    async def add_branch_note(self, lead_id: int, studio: str) -> None:
        text = f"Филиал из формы не сопоставлен автоматически: {studio}"
        await self._request(
            "POST",
            f"/api/v4/leads/{lead_id}/notes",
            json=[{"note_type": "common", "params": {"text": text}}],
            retry_writes=False,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        retry_writes: bool,
        **kwargs: Any,
    ) -> httpx.Response:
        attempts = 3 if method == "GET" or retry_writes else 1
        async with httpx.AsyncClient(
            base_url=f"https://{self.domain}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "annaelle-landing-leads/1.0",
            },
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            for attempt in range(attempts):
                try:
                    response = await client.request(method, path, **kwargs)
                except httpx.RequestError:
                    if attempt + 1 >= attempts:
                        raise
                    await asyncio.sleep(0.25 * (attempt + 1))
                    continue
                if response.status_code in {429, 500, 502, 503, 504} and attempt + 1 < attempts:
                    await asyncio.sleep(0.25 * (attempt + 1))
                    continue
                if response.status_code >= 400:
                    raise KommoError(
                        f"KOMMO_HTTP_{response.status_code}",
                        retryable=response.status_code in {429, 500, 502, 503, 504},
                    )
                return response
        raise KommoError("KOMMO_REQUEST_FAILED", retryable=True)

    @staticmethod
    def _contact_has_exact_phone(contact: dict[str, Any], expected: str) -> bool:
        expected_digits = re.sub(r"\D", "", expected)
        for field in contact.get("custom_fields_values") or []:
            is_phone = field.get("field_code") == "PHONE" or str(
                field.get("field_name", "")
            ).lower() in {"phone", "телефон"}
            if not is_phone:
                continue
            for item in field.get("values") or []:
                if re.sub(r"\D", "", str(item.get("value", ""))) == expected_digits:
                    return True
        return False
