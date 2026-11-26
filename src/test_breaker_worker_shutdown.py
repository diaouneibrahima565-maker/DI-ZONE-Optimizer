
import threading
import unittest

from unittest.mock import Mock

from breaker_worker import BreakerActionWorker


class TestBreakerWorkerShutdown(unittest.TestCase):

    def setUp(self):
        self.controller = Mock()

        self.controller.approve_and_execute.return_value = {
            "status": "completed"
        }

        self.worker = BreakerActionWorker(
            self.controller
        )

    def test_01_worker_starts_open(self):
        self.assertIs(
            self.worker._closed,
            False
        )

    def test_02_shutdown_closes_worker(self):
        self.worker.shutdown()

        self.assertIs(
            self.worker._closed,
            True
        )

    def test_03_closed_worker_rejects_actions(self):
        self.worker.shutdown()

        with self.assertRaises(RuntimeError):
            self.worker.start("action-123")

        self.controller.approve_and_execute.assert_not_called()

    def test_04_shutdown_is_idempotent(self):
        self.worker.shutdown()
        self.worker.shutdown()

        self.assertIs(
            self.worker._closed,
            True
        )

        with self.assertRaises(RuntimeError):
            self.worker.start("action-456")

    def test_05_running_action_can_finish_after_shutdown(self):
        started = threading.Event()
        release = threading.Event()

        def slow_action(action_id):
            started.set()
            release.wait(timeout=3)
            return {"status": "completed"}

        self.controller.approve_and_execute.side_effect = (
            slow_action
        )

        self.worker.start("action-789")

        try:
            self.assertTrue(
                started.wait(timeout=2)
            )

            self.worker.shutdown()

            self.assertTrue(
                self.worker._thread.is_alive()
            )

            with self.assertRaises(RuntimeError):
                self.worker.start("another-action")

        finally:
            release.set()

            self.worker._thread.join(timeout=3)

        event = self.worker.results.get(timeout=2)

        self.assertEqual(
            event["action_id"],
            "action-789"
        )

        self.assertEqual(
            event["status"],
            "completed"
        )

        self.assertIs(
            event["success"],
            True
        )

        self.controller.approve_and_execute.assert_called_once_with(
            "action-789"
        )

    def test_06_shutdown_does_not_wait_for_running_work(self):
        started = threading.Event()
        release = threading.Event()
        shutdown_finished = threading.Event()

        def slow_action(action_id):
            started.set()
            release.wait(timeout=3)
            return {"status": "completed"}

        self.controller.approve_and_execute.side_effect = (
            slow_action
        )

        self.worker.start("action-slow")

        def request_shutdown():
            self.worker.shutdown()
            shutdown_finished.set()

        shutdown_thread = threading.Thread(
            target=request_shutdown,
            daemon=True
        )

        try:
            self.assertTrue(
                started.wait(timeout=2)
            )

            shutdown_thread.start()

            self.assertTrue(
                shutdown_finished.wait(timeout=1),
                "shutdown() blocked on running work"
            )

        finally:
            release.set()

            if shutdown_thread.ident is not None:
                shutdown_thread.join(timeout=3)

            self.worker._thread.join(timeout=3)

        self.assertFalse(
            self.worker._thread.is_alive()
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
