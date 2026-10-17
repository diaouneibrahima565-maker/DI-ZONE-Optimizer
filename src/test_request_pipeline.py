
import queue
import threading
import unittest
from unittest.mock import Mock, patch

from request_lifecycle import (
    RequestLifecycle,
    RequestLifecycleError,
    REQUEST_IDLE,
    REQUEST_GENERATING,
    REQUEST_CLOSED
)
from request_worker import run_ai_worker


class TestRequestPipeline(unittest.TestCase):

    def setUp(self):
        self.lifecycle = RequestLifecycle()
        self.results = queue.Queue()

        self.messages = [
            {
                "role": "user",
                "content": "Explain Python."
            }
        ]

    def start_request(self, request_id="request_1"):
        return self.lifecycle.start(
            request_id,
            "folder_1",
            "conversation_1"
        )

    def generate(self, request_id, fake_model):
        run_ai_worker(
            request_id,
            "folder_1",
            "conversation_1",
            "ollama",
            self.messages,
            self.results,
            generate_reply=fake_model
        )

        return self.results.get_nowait()

    def test_01_successful_request_flow(self):
        self.start_request()

        result = self.generate(
            "request_1",
            Mock(return_value="Python is a programming language.")
        )

        self.assertTrue(
            self.lifecycle.matches(result["request_id"])
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["conversation_id"],
            "conversation_1"
        )

        self.assertTrue(
            self.lifecycle.finish(result["request_id"])
        )
        self.assertEqual(self.lifecycle.state, REQUEST_IDLE)

    def test_02_provider_failure_recovery(self):
        self.start_request()

        with patch("request_worker.logger.exception"):
            result = self.generate(
                "request_1",
                Mock(side_effect=RuntimeError("Ollama unavailable"))
            )

        self.assertEqual(result["status"], "error")

        self.assertTrue(
            self.lifecycle.finish(result["request_id"])
        )
        self.assertEqual(self.lifecycle.state, REQUEST_IDLE)

    def test_03_prevent_overlapping_requests(self):
        self.start_request()

        with self.assertRaises(RequestLifecycleError):
            self.start_request("request_2")

        self.assertEqual(
            self.lifecycle.state,
            REQUEST_GENERATING
        )

    def test_04_stale_result_is_rejected(self):
        self.start_request("request_1")
        self.lifecycle.finish("request_1")

        self.start_request("request_2")

        stale_result = self.generate(
            "request_1",
            Mock(return_value="Old response")
        )

        self.assertFalse(
            self.lifecycle.matches(stale_result["request_id"])
        )
        self.assertFalse(
            self.lifecycle.finish(stale_result["request_id"])
        )

        self.assertTrue(
            self.lifecycle.matches("request_2")
        )

    def test_05_shutdown_rejects_late_results(self):
        self.start_request()
        self.lifecycle.close()

        result = self.generate(
            "request_1",
            Mock(return_value="Late response")
        )

        self.assertEqual(self.lifecycle.state, REQUEST_CLOSED)
        self.assertFalse(
            self.lifecycle.matches(result["request_id"])
        )

    def test_06_delayed_worker(self):
        started = threading.Event()
        release = threading.Event()

        def fake_slow_model(messages, provider_name):
            started.set()
            release.wait(timeout=3)
            return "Delayed response"

        self.start_request()

        worker = threading.Thread(
            target=run_ai_worker,
            args=(
                "request_1",
                "folder_1",
                "conversation_1",
                "ollama",
                self.messages,
                self.results,
                fake_slow_model
            ),
            daemon=True
        )

        worker.start()

        try:
            self.assertTrue(started.wait(timeout=3))
            self.assertTrue(self.results.empty())
            self.assertEqual(
                self.lifecycle.state,
                REQUEST_GENERATING
            )
        finally:
            release.set()
            worker.join(timeout=3)

        self.assertFalse(worker.is_alive())

        result = self.results.get_nowait()

        self.assertEqual(result["status"], "success")
        self.assertTrue(
            self.lifecycle.finish(result["request_id"])
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
