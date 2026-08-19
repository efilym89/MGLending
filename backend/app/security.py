from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import unicodedata
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class PayloadCipher:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode("ascii"))

    def encrypt(self, payload: dict[str, Any]) -> bytes:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        return self._fernet.encrypt(raw)

    def decrypt(self, value: bytes) -> dict[str, Any]:
        try:
            decoded = self._fernet.decrypt(value)
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt stored payload") from exc
        result = json.loads(decoded)
        if not isinstance(result, dict):
            raise ValueError("Stored payload is not an object")
        return result


def keyed_hash(value: str, key: str) -> str:
    return hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()


def normalize_meta_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def normalize_meta_phone(value: str) -> str:
    return re.sub(r"\D", "", value)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def is_valid_fernet_key(value: str) -> bool:
    try:
        return len(base64.urlsafe_b64decode(value.encode())) == 32
    except (ValueError, TypeError):
        return False
