"""Symmetric encryption for secrets stored in the database.

Used to protect per-tenant third-party API tokens (currently Meta
WhatsApp Cloud API access tokens). Keep the Fernet key
(`VIGILANTE_NOTIFY_ENCRYPTION_KEY`) out of source control — rotating it
invalidates all encrypted blobs on disk, so generate once per
deployment and store in a secret manager.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class EncryptionUnavailableError(RuntimeError):
    """Raised when an encryption operation is attempted without a configured key."""


class SecretDecryptError(RuntimeError):
    """Raised when a ciphertext cannot be decrypted (key mismatch / corruption)."""


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.NOTIFY_ENCRYPTION_KEY.strip()
    if not key:
        raise EncryptionUnavailableError(
            "VIGILANTE_NOTIFY_ENCRYPTION_KEY is not configured. "
            "Generate one with: python -c \"from cryptography.fernet import "
            "Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise EncryptionUnavailableError(
            f"VIGILANTE_NOTIFY_ENCRYPTION_KEY is not a valid Fernet key: {exc}"
        ) from exc


def encryption_available() -> bool:
    """True iff a usable encryption key is configured. Cheap to call."""
    try:
        _fernet()
        return True
    except EncryptionUnavailableError:
        return False


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a UTF-8 string and return ciphertext as a base64 ASCII string."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str) -> str:
    """Inverse of `encrypt_secret`. Raises `SecretDecryptError` on bad ciphertext."""
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise SecretDecryptError("Stored secret could not be decrypted") from exc
