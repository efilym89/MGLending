#!/usr/bin/env python3
"""Idempotently register the landing incoming-message webhook in Kommo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib import error, parse, request


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def api_request(
    url: str,
    token: str,
    *,
    method: str = "GET",
    body: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            payload = response.read()
            return response.status, json.loads(payload) if payload else {}
    except error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kommo API returned HTTP {exc.code}: {payload[:500]}") from exc


def normalize_domain(value: str) -> str:
    domain = value.strip().rstrip("/")
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"
    return domain


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("/srv/annaelle/env/landing-leads.env"),
    )
    args = parser.parse_args()
    env = load_env(args.env_file)

    required = ("KOMMO_DOMAIN", "KOMMO_LONG_LIVED_TOKEN", "KOMMO_WEBHOOK_SECRET")
    missing = [name for name in required if not env.get(name)]
    if missing:
        print(f"Missing required variables: {', '.join(missing)}", file=sys.stderr)
        return 2

    api_base = normalize_domain(env["KOMMO_DOMAIN"])
    token = env["KOMMO_LONG_LIVED_TOKEN"]
    destination = (
        "https://api.annaellebot.com/landing-leads/v1/kommo/"
        f"webhooks/incoming-message/{env['KOMMO_WEBHOOK_SECRET']}"
    )
    endpoint = f"{api_base}/api/v4/webhooks"
    query = parse.urlencode({"filter[destination]": destination})
    _, current = api_request(f"{endpoint}?{query}", token)
    webhooks = current.get("_embedded", {}).get("webhooks", [])

    for webhook in webhooks:
        if webhook.get("destination") == destination:
            settings = set(webhook.get("settings") or [])
            if "add_message" in settings and not webhook.get("disabled", False):
                print(f"Webhook already active (id={webhook.get('id')}).")
                return 0

    _, created = api_request(
        endpoint,
        token,
        method="POST",
        body={"destination": destination, "settings": ["add_message"]},
    )
    print(f"Webhook registered (id={created.get('id')}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
