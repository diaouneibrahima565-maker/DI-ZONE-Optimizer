
import threading
import unittest

from unittest.mock import Mock

from breaker_worker import BreakerActionWorker


class TestBreakerActionWorker(unittest.TestCase):

    def setUp(self):
        self.controller = Mock()
        self.controller.approve_and_execute.return_value = {
            "status": "completed"
        }

        self.worker = BreakerActionWorker(
            self.controller
        )

    def get_result(self):
        event = self.worker.results.get(timeout=3)

        self.worker._thread.join(timeout=3)

        return event

    def test_01_does_not_execute_during_initialization(self):
        self.controller.approve_and_execute.assert_not_called()

    def test_02_successful_execution(self):
        self.worker.start("action-123")

        event = self.get_result()

        self.assertEqual(
            event["action_id"],
            "action-123"
        )

        self.assertEqual(
            event["status"],
            "completed"
        )

        self.assertIs(event["success"], True)

        self.controller.approve_and_execute.assert_called_once_with(
            "action-123"
        )

    def test_03_failed_execution_result(self):
        self.controller.approve_and_execute.return_value = {
            "status": "failed"
        }

        self.worker.start("action-456")

        event = self.get_result()

        self.assertEqual(event["status"], "failed")
        self.assertIs(event["success"], False)

    def test_04_exception_reports_failure(self):
        self.controller.approve_and_execute.side_effect = OSError(
            "Simulated storage failure"
        )

        self.worker.start("action-789")

        event = self.get_result()

        self.assertEqual(event["status"], "failed")
        self.assertIs(event["success"], False)
        self.assertEqual(event["error_type"], "OSError")

    def test_05_invalid_action_id(self):
        for invalid_id in ("", "   ", None, 123):
            with self.subTest(action_id=invalid_id):
                with self.assertRaises(ValueError):
                    self.worker.start(invalid_id)

        self.controller.approve_and_execute.assert_not_called()

    def test_06_prevents_concurrent_execution(self):
        started = threading.Event()
        release = threading.Event()

        def slow_controller(action_id):
            started.set()
            release.wait(timeout=3)
            return {"status": "completed"}

        self.controller.approve_and_execute.side_effect = (
            slow_controller
        )

        try:
            self.worker.start("first-action")

            self.assertTrue(
                started.wait(timeout=2)
            )

            with self.assertRaises(RuntimeError):
                self.worker.start("second-action")

        finally:
            release.set()

            if self.worker._thread is not None:
                self.worker._thread.join(timeout=3)

        self.assertFalse(
            self.worker._thread.is_alive()
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
