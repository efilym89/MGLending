from __future__ import annotations

import json
import re
from urllib.parse import parse_qs

MESSAGE_FIELD_RE = re.compile(r"^add\[(\d+)]\[([^]]+)]$")
SUBMISSION_ID_RE = re.compile(
    r"(?<![A-Za-z0-9._:-])(?:"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"|annaelle-\d{10,}-[0-9a-f]{6,}"
    r")(?![A-Za-z0-9._:-])",
    re.IGNORECASE,
)


def parse_incoming_messages(body: bytes, content_type: str) -> list[dict[str, str]]:
    if "application/json" in content_type.lower():
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return []
        raw_events = payload.get("add", []) if isinstance(payload, dict) else []
        return [
            {str(key): str(value) for key, value in item.items() if not isinstance(value, dict)}
            for item in raw_events
            if isinstance(item, dict)
        ]

    try:
        fields = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError:
        return []
    events: dict[int, dict[str, str]] = {}
    for key, values in fields.items():
        match = MESSAGE_FIELD_RE.match(key)
        if not match or not values:
            continue
        index, field = match.groups()
        events.setdefault(int(index), {})[field] = values[-1]
    return [events[index] for index in sorted(events)]


def extract_submission_id(text: str) -> str | None:
    match = SUBMISSION_ID_RE.search(text)
    return match.group(0) if match else None


def telegram_link_requests(
    body: bytes, content_type: str
) -> list[tuple[str, int]]:
    requests: list[tuple[str, int]] = []
    for event in parse_incoming_messages(body, content_type):
        if event.get("type", "").lower() != "incoming":
            continue
        if event.get("origin", "").lower() != "telegram":
            continue
        submission_id = extract_submission_id(event.get("text", ""))
        lead_id = event.get("entity_id") or event.get("element_id")
        if not submission_id or not lead_id:
            continue
        try:
            parsed_lead_id = int(lead_id)
        except ValueError:
            continue
        if parsed_lead_id > 0:
            requests.append((submission_id, parsed_lead_id))
    return requests
