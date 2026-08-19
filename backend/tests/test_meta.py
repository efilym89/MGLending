from __future__ import annotations

import hashlib

import httpx
import pytest

from app.meta import MetaClient
from app.models import LeadSubmission


def test_meta_event_uses_shared_event_id_and_excludes_sensitive_fields(
    submission: LeadSubmission,
) -> None:
    client = MetaClient(dataset_id="123", access_token="token")
    event = client.build_event(
        submission,
        client_ip="203.0.113.10",
        client_user_agent="Test Browser",
    )
    assert event["event_name"] == "Lead"
    assert event["event_id"] == submission.submission_id
    assert event["action_source"] == "website"
    assert event["user_data"]["ph"] == [hashlib.sha256(b"998901234567").hexdigest()]
    serialized = str(event)
    assert submission.comment not in serialized
    assert submission.offer not in serialized
    assert submission.studio not in serialized
    assert submission.phone not in serialized


@pytest.mark.anyio
async def test_meta_access_token_is_sent_in_authorization_header(
    submission: LeadSubmission,
) -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json={"events_received": 1, "fbtrace_id": "trace"})

    client = MetaClient(
        dataset_id="123",
        access_token="secret-token",
        transport=httpx.MockTransport(handler),
    )
    event = client.build_event(
        submission,
        client_ip="203.0.113.10",
        client_user_agent="Test Browser",
    )

    assert await client.send_event(event) == "trace"
    assert captured_request is not None
    assert "secret-token" not in str(captured_request.url)
    assert captured_request.headers["authorization"] == "Bearer secret-token"
