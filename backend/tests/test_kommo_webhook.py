from __future__ import annotations

from urllib.parse import urlencode

from app.kommo_webhook import extract_submission_id, telegram_link_requests

SUBMISSION_ID = "018f1234-5678-7abc-8def-0123456789ab"


def test_extract_submission_id_from_prepared_message() -> None:
    text = f"Здравствуйте!\nКод заявки: {SUBMISSION_ID}\n#META_LANDING"
    assert extract_submission_id(text) == SUBMISSION_ID


def test_parse_urlencoded_telegram_message() -> None:
    body = urlencode(
        {
            "add[0][text]": f"Код заявки: {SUBMISSION_ID}\n#META_LANDING",
            "add[0][origin]": "telegram",
            "add[0][type]": "incoming",
            "add[0][entity_id]": "3001",
        }
    ).encode()
    assert telegram_link_requests(body, "application/x-www-form-urlencoded") == [
        (SUBMISSION_ID, 3001)
    ]


def test_ignore_outgoing_and_non_telegram_messages() -> None:
    body = urlencode(
        {
            "add[0][text]": SUBMISSION_ID,
            "add[0][origin]": "telegram",
            "add[0][type]": "outgoing",
            "add[0][entity_id]": "3001",
            "add[1][text]": SUBMISSION_ID,
            "add[1][origin]": "whatsapp",
            "add[1][type]": "incoming",
            "add[1][entity_id]": "3002",
        }
    ).encode()
    assert telegram_link_requests(body, "application/x-www-form-urlencoded") == []
