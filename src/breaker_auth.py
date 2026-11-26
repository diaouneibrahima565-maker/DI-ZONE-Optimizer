"""Local Breaker credential enrollment and verification.

This protects the Breaker interface from casual use; it is not an operating
system security boundary.
"""

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from tempfile import NamedTemporaryFile


CREDENTIAL_FILE = Path(__file__).resolve().parent.parent / "data" / "breaker_credentials.json"
KDF_ITERATIONS = 600_000
SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 1024


class CredentialStoreError(Exception):
    """Raised when the local credential store cannot be safely used."""


def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, KDF_ITERATIONS
    )


class BreakerCredentialStore:
    """Store only a salted PBKDF2 hash and verify Breaker passwords."""

    def __init__(self, path=None):
        self.path = Path(path or CREDENTIAL_FILE)

    def is_enrolled(self) -> bool:
        return self.path.exists()

    def enroll(self, password: str, confirmation: str) -> None:
        if self.is_enrolled():
            raise CredentialStoreError("A Breaker credential is already enrolled.")
        if not isinstance(password, str) or not isinstance(confirmation, str):
            raise CredentialStoreError("Enter a valid password and confirmation.")
        if password != confirmation:
            raise CredentialStoreError("The password entries do not match.")
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            raise CredentialStoreError(
                f"Use a password between {MIN_PASSWORD_LENGTH} and "
                f"{MAX_PASSWORD_LENGTH} characters."
            )

        salt = secrets.token_bytes(SALT_BYTES)
        credential = {
            "schema_version": 1,
            "kdf": "pbkdf2_hmac_sha256",
            "iterations": KDF_ITERATIONS,
            "salt": salt.hex(),
            "password_hash": _derive_key(password, salt).hex(),
        }
        temporary_path = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as credential_file:
                temporary_path = Path(credential_file.name)
                json.dump(credential, credential_file)
                credential_file.flush()
                os.fsync(credential_file.fileno())
            try:
                os.chmod(temporary_path, 0o600)
            except OSError:
                # Windows access is governed by the containing directory's ACL.
                pass
            temporary_path.replace(self.path)
        except OSError as error:
            raise CredentialStoreError("Could not save the Breaker credential.") from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def verify(self, password: str) -> bool:
        if not isinstance(password, str) or len(password) > MAX_PASSWORD_LENGTH:
            return False
        try:
            credential = json.loads(self.path.read_text(encoding="utf-8"))
            salt = bytes.fromhex(credential["salt"])
            expected_hash = bytes.fromhex(credential["password_hash"])
        except FileNotFoundError as error:
            raise CredentialStoreError("No Breaker credential is enrolled.") from error
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise CredentialStoreError("The Breaker credential file is invalid.") from error

        if (
            not isinstance(credential, dict)
            or credential.get("schema_version") != 1
            or credential.get("kdf") != "pbkdf2_hmac_sha256"
            or credential.get("iterations") != KDF_ITERATIONS
            or len(salt) != SALT_BYTES
            or len(expected_hash) != hashlib.sha256().digest_size
        ):
            raise CredentialStoreError("The Breaker credential file is invalid.")

        candidate_hash = _derive_key(password, salt)
        return hmac.compare_digest(candidate_hash, expected_hash)


class AuthenticationThrottle:
    """Apply a short in-memory delay after repeated failed unlock attempts."""

    def __init__(self, clock=None):
        import time

        self._clock = clock or time.monotonic
        self._failures = 0
        self._locked_until = 0.0

    def remaining_seconds(self) -> int:
        remaining = self._locked_until - self._clock()
        return max(0, int(remaining + 0.999))

    def record_failure(self) -> int:
        self._failures += 1
        if self._failures >= 5:
            exponent = min(self._failures - 5, 6)
            delay = min(300, 5 * (2 ** exponent))
            self._locked_until = self._clock() + delay
        return self.remaining_seconds()

    def record_success(self) -> None:
        self._failures = 0
        self._locked_until = 0.0
