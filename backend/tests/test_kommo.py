from __future__ import annotations

from app.kommo import KommoClient
from app.models import LeadSubmission


def test_incoming_payload_stays_unsorted(schema: dict, submission: LeadSubmission) -> None:
    client = KommoClient(domain="example.kommo.com", token="token", schema=schema)
    payload = client.build_incoming_payload(
        submission,
        client_ip="203.0.113.10",
        existing_contact_id=None,
    )
    lead = payload["_embedded"]["leads"][0]
    contact = payload["_embedded"]["contacts"][0]

    assert payload["pipeline_id"] == 14282171
    assert payload["source_uid"] == "annaelle_landing_v1"
    assert "status_id" not in lead
    assert lead["_embedded"]["tags"] == [{"id": 4754}]
    assert contact["custom_fields_values"][0]["field_code"] == "PHONE"
    assert contact["custom_fields_values"][0]["values"][0]["value"] == "+998901234567"


def test_incoming_payload_contains_tracking_fields(
    schema: dict, submission: LeadSubmission
) -> None:
    client = KommoClient(domain="example.kommo.com", token="token", schema=schema)
    payload = client.build_incoming_payload(
        submission,
        client_ip="203.0.113.10",
        existing_contact_id=123,
    )
    lead = payload["_embedded"]["leads"][0]
    values = {item["field_id"]: item["values"][0] for item in lead["custom_fields_values"]}
    assert payload["_embedded"]["contacts"] == [{"id": 123}]
    assert values[155672]["value"] == submission.submission_id
    assert values[155678]["value"] == "111"
    assert values[155680]["value"] == "222"
    assert values[155682]["value"] == "333"
    assert values[155684]["value"] == "instagram_stories"
    assert values[62720] == {"enum_id": 50404}
    assert values[23108]["value"] == "meta"


def test_unknown_branch_is_preserved_without_fake_enum(
    schema: dict, submission: LeadSubmission
) -> None:
    changed = submission.model_copy(update={"studio": "Подобрать ближайшую"})
    client = KommoClient(domain="example.kommo.com", token="token", schema=schema)
    payload = client.build_incoming_payload(
        changed,
        client_ip="203.0.113.10",
        existing_contact_id=None,
    )
    fields = payload["_embedded"]["leads"][0]["custom_fields_values"]
    field_ids = {item["field_id"] for item in fields}
    assert 62720 not in field_ids
    comment = next(item for item in fields if item["field_id"] == 155676)
    assert "Подобрать ближайшую" in comment["values"][0]["value"]
