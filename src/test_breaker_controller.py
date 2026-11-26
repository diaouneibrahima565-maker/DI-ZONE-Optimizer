
import unittest
from unittest.mock import Mock

from breaker_actions import BreakerActionError
from breaker_approval import ActionApprovalError
from breaker_execution import (
    BreakerExecutionError
)
from breaker_controller import BreakerController


class TestBreakerController(unittest.TestCase):

    def setUp(self):
        self.writer = Mock(return_value=True)
        self.controller = BreakerController(self.writer)

    def propose(self, content="Learn Python"):
        return self.controller.submit_memory(content)

    def events(self, action_id):
        history = self.controller.get_history(action_id)
        return [entry["event"] for entry in history]

    def test_01_creates_pending_proposal(self):
        proposal = self.propose()

        self.assertEqual(
            proposal["status"],
            "pending_approval"
        )

        self.assertEqual(
            proposal["action_type"],
            "memory_write"
        )

        self.writer.assert_not_called()

    def test_02_approval_executes_memory(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        result = self.controller.approve_and_execute(
            action_id
        )

        self.assertEqual(
            result["status"],
            "completed"
        )

        self.writer.assert_called_once_with(
            "Learn Python"
        )

    def test_03_records_successful_workflow(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        self.controller.approve_and_execute(action_id)

        self.assertEqual(
            self.events(action_id),
            [
                "proposed",
                "approved",
                "execution_requested",
                "completed"
            ]
        )

    def test_04_cancellation_prevents_execution(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        canceled = self.controller.cancel_action(
            action_id
        )

        self.assertEqual(
            canceled["status"],
            "canceled"
        )

        self.writer.assert_not_called()

        self.assertEqual(
            self.events(action_id),
            ["proposed", "canceled"]
        )

    def test_05_cannot_approve_canceled_action(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        self.controller.cancel_action(action_id)

        with self.assertRaises(ActionApprovalError):
            self.controller.approve_and_execute(action_id)

        self.writer.assert_not_called()

    def test_06_cannot_approve_twice(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        self.controller.approve_and_execute(action_id)

        with self.assertRaises(ActionApprovalError):
            self.controller.approve_and_execute(action_id)

        self.writer.assert_called_once()

    def test_07_rejects_invalid_content(self):
        with self.assertRaises(BreakerActionError):
            self.controller.submit_memory("   ")

        self.writer.assert_not_called()

        self.assertEqual(
            self.controller.get_history(),
            []
        )

    def test_08_handles_writer_failure(self):
        self.writer.side_effect = OSError(
            "Simulated storage failure"
        )

        proposal = self.propose()
        action_id = proposal["action_id"]

        with self.assertRaises(BreakerExecutionError):
            self.controller.approve_and_execute(action_id)

        self.assertEqual(
            self.events(action_id)[-1],
            "failed"
        )

    def test_09_history_is_an_independent_copy(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        history = self.controller.get_history()
        history[0]["event"] = "completed"

        self.assertEqual(
            self.events(action_id),
            ["proposed"]
        )

    def test_10_invalid_writer_is_rejected(self):
        with self.assertRaises(BreakerExecutionError):
            BreakerController(None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
