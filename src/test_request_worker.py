
import queue
import threading
import unittest
from unittest.mock import Mock, patch

from request_worker import run_ai_worker


class TestRequestWorker(unittest.TestCase):

    def setUp(self):
        self.results = queue.Queue()

        self.messages = [
            {
                "role": "user",
                "content": "Explain Python lists."
            }
        ]

        self.request_id = "request_001"
        self.folder_id = "folder_general"
        self.conversation_id = "chat_python"

    def run_worker(self, generator):
        run_ai_worker(
            self.request_id,
            self.folder_id,
            self.conversation_id,
            "ollama",
            self.messages,
            self.results,
            generate_reply=generator
        )

        return self.results.get_nowait()

    def test_01_successful_response(self):

        fake_model = Mock(return_value="Python lists store items.")

        result = self.run_worker(fake_model)

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["response"],
            "Python lists store items."
        )

    def test_02_correct_request_identifiers(self):

        fake_model = Mock(return_value="Response")

        result = self.run_worker(fake_model)

        self.assertEqual(result["request_id"], self.request_id)
        self.assertEqual(result["folder_id"], self.folder_id)
        self.assertEqual(
            result["conversation_id"],
            self.conversation_id
        )

    def test_03_correct_provider_arguments(self):

        fake_model = Mock(return_value="Response")

        self.run_worker(fake_model)

        fake_model.assert_called_once_with(
            self.messages,
            provider_name="ollama"
        )

    def test_04_provider_failure(self):

        fake_model = Mock(
            side_effect=RuntimeError("Model unavailable")
        )

        with patch("request_worker.logger.exception"):
            result = self.run_worker(fake_model)

        self.assertEqual(result["status"], "error")

        self.assertEqual(
            result["response"],
            "AI generation failed. Please try again."
        )

    def test_05_background_thread(self):

        fake_model = Mock(return_value="Generated response")

        worker = threading.Thread(
            target=run_ai_worker,
            args=(
                self.request_id,
                self.folder_id,
                self.conversation_id,
                "ollama",
                self.messages,
                self.results,
                fake_model
            ),
            daemon=True
        )

        worker.start()
        worker.join(timeout=3)

        self.assertFalse(worker.is_alive())

        result = self.results.get_nowait()

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["response"],
            "Generated response"
        )

    def test_06_worker_waits_without_blocking_caller(self):

        started = threading.Event()
        release = threading.Event()

        def slow_model(messages, provider_name):
            started.set()
            release.wait(timeout=3)
            return "Delayed response"

        worker = threading.Thread(
            target=run_ai_worker,
            args=(
                self.request_id,
                self.folder_id,
                self.conversation_id,
                "ollama",
                self.messages,
                self.results,
                slow_model
            ),
            daemon=True
        )

        worker.start()

        try:
            self.assertTrue(started.wait(timeout=3))
            self.assertTrue(self.results.empty())

        finally:
            release.set()
            worker.join(timeout=3)

        self.assertFalse(worker.is_alive())

        result = self.results.get_nowait()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["response"], "Delayed response")


if __name__ == "__main__":
    unittest.main(verbosity=2)
