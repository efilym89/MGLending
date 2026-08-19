from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.models import LeadSubmission
from app.security import PayloadCipher, normalize_meta_name, normalize_meta_phone, sha256_hex


def test_rejects_incomplete_uzbek_phone(submission: LeadSubmission) -> None:
    with pytest.raises(ValidationError):
        LeadSubmission.model_validate({**submission.model_dump(), "phone": "+99894039046"})


def test_cipher_round_trip() -> None:
    cipher = PayloadCipher(Fernet.generate_key().decode())
    original = {"phone": "+998901234567", "name": "Sevara"}
    encrypted = cipher.encrypt(original)
    assert b"+998901234567" not in encrypted
    assert cipher.decrypt(encrypted) == original


def test_meta_normalization() -> None:
    assert normalize_meta_phone("+998 90 123 45 67") == "998901234567"
    assert normalize_meta_name("  SEVARA   U. ") == "sevara u."
    assert len(sha256_hex("998901234567")) == 64
