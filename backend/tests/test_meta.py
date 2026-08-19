from __future__ import annotations

import hashlib

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
