import json
import tempfile
import unittest
from pathlib import Path

from breaker_auth import (
    AuthenticationThrottle,
    BreakerCredentialStore,
    CredentialStoreError,
    KDF_ITERATIONS,
)


class TestBreakerCredentialStore(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "credentials.json"
        self.store = BreakerCredentialStore(self.path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_enrollment_stores_salted_hash_and_verifies_password(self):
        self.store.enroll("correct horse battery", "correct horse battery")

        credential = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertNotIn("correct horse battery", self.path.read_text(encoding="utf-8"))
        self.assertEqual(credential["iterations"], KDF_ITERATIONS)
        self.assertTrue(self.store.verify("correct horse battery"))
        self.assertFalse(self.store.verify("incorrect password"))

    def test_enrollment_rejects_mismatch_short_password_and_reenrollment(self):
        with self.assertRaises(CredentialStoreError):
            self.store.enroll("short", "short")
        with self.assertRaises(CredentialStoreError):
            self.store.enroll("long enough password", "different password")

        self.store.enroll("long enough password", "long enough password")
        with self.assertRaises(CredentialStoreError):
            self.store.enroll("another long password", "another long password")

    def test_corrupt_credentials_fail_closed(self):
        self.path.write_text("not-json", encoding="utf-8")
        with self.assertRaises(CredentialStoreError):
            self.store.verify("any password")


class TestAuthenticationThrottle(unittest.TestCase):
    def test_repeated_failures_delay_unlock_and_success_resets(self):
        now = [100.0]
        throttle = AuthenticationThrottle(clock=lambda: now[0])

        for _ in range(4):
            self.assertEqual(throttle.record_failure(), 0)
        self.assertEqual(throttle.record_failure(), 5)
        self.assertEqual(throttle.remaining_seconds(), 5)

        now[0] += 5
        self.assertEqual(throttle.remaining_seconds(), 0)
        throttle.record_success()
        self.assertEqual(throttle.record_failure(), 0)

    def test_long_failure_streak_is_capped_at_five_minutes(self):
        throttle = AuthenticationThrottle(clock=lambda: 100.0)

        for _ in range(20):
            throttle.record_failure()

        self.assertEqual(throttle.remaining_seconds(), 300)


if __name__ == "__main__":
    unittest.main()
