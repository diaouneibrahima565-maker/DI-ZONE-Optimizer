
import unittest

from request_lifecycle import (
    RequestLifecycle,
    RequestLifecycleError,
    REQUEST_IDLE,
    REQUEST_GENERATING,
    REQUEST_CLOSED
)


class TestRequestLifecycle(unittest.TestCase):

    def setUp(self):
        self.lifecycle = RequestLifecycle()

    def start_request(self, request_id="request_1"):
        return self.lifecycle.start(
            request_id,
            "folder_general",
            "chat_python"
        )

    def test_01_initial_state(self):
        self.assertEqual(self.lifecycle.state, REQUEST_IDLE)
        self.assertIsNone(self.lifecycle.active_request)

    def test_02_start_request(self):
        result = self.start_request()

        self.assertEqual(
            self.lifecycle.state,
            REQUEST_GENERATING
        )
        self.assertEqual(
            result["request_id"],
            "request_1"
        )

    def test_03_active_request_matches(self):
        self.start_request()

        self.assertTrue(self.lifecycle.matches("request_1"))

    def test_04_wrong_request_does_not_match(self):
        self.start_request()

        self.assertFalse(self.lifecycle.matches("request_2"))

    def test_05_finish_matching_request(self):
        self.start_request()

        self.assertTrue(self.lifecycle.finish("request_1"))
        self.assertEqual(self.lifecycle.state, REQUEST_IDLE)
        self.assertIsNone(self.lifecycle.active_request)

    def test_06_wrong_request_cannot_finish(self):
        self.start_request()

        self.assertFalse(self.lifecycle.finish("request_2"))
        self.assertEqual(
            self.lifecycle.state,
            REQUEST_GENERATING
        )

    def test_07_prevent_simultaneous_requests(self):
        self.start_request()

        with self.assertRaises(RequestLifecycleError):
            self.start_request("request_2")

    def test_08_invalid_identifiers(self):
        for invalid in (None, "", " ", 123):
            with self.subTest(value=invalid):
                with self.assertRaises(RequestLifecycleError):
                    self.lifecycle.start(
                        invalid,
                        "folder_general",
                        "chat_python"
                    )

        self.assertEqual(self.lifecycle.state, REQUEST_IDLE)

    def test_09_close(self):
        self.start_request()
        self.lifecycle.close()

        self.assertEqual(self.lifecycle.state, REQUEST_CLOSED)
        self.assertIsNone(self.lifecycle.active_request)

    def test_10_cannot_start_after_close(self):
        self.lifecycle.close()

        with self.assertRaises(RequestLifecycleError):
            self.start_request()

    def test_11_stale_result_after_close(self):
        self.start_request()
        self.lifecycle.close()

        self.assertFalse(self.lifecycle.matches("request_1"))
        self.assertFalse(self.lifecycle.finish("request_1"))

    def test_12_second_request_after_completion(self):
        self.start_request()
        self.lifecycle.finish("request_1")

        result = self.start_request("request_2")

        self.assertEqual(result["request_id"], "request_2")
        self.assertEqual(
            self.lifecycle.state,
            REQUEST_GENERATING
        )

    def test_13_request_copy_is_independent(self):
        result = self.start_request()
        result["conversation_id"] = "modified"

        self.assertEqual(
            self.lifecycle.active_request["conversation_id"],
            "chat_python"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
