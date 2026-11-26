
import unittest

from datetime import datetime
from unittest.mock import Mock

from breaker_workflow import BreakerWorkflow
from breaker_approval import ActionApprovalError
from breaker_execution import BreakerExecutionError


class TestBreakerWorkflow(unittest.TestCase):

    def setUp(self):
        self.writer = Mock(return_value=True)
        self.workflow = BreakerWorkflow(self.writer)

    def propose(self, content="Learn Python"):
        return self.workflow.propose(
            "memory_write",
            {"content": content}
        )

    def approved_action(self, content="Learn Python"):
        proposal = self.propose(content)
        self.workflow.approve(proposal["action_id"])
        return proposal["action_id"]

    def events_for(self, action_id):
        history = self.workflow.get_history(action_id)
        return [record["event"] for record in history]

    def test_01_records_proposal(self):
        proposal = self.propose()
        events = self.events_for(proposal["action_id"])

        self.assertEqual(events, ["proposed"])

    def test_02_records_approval(self):
        action_id = self.approved_action()

        self.assertEqual(
            self.events_for(action_id),
            ["proposed", "approved"]
        )

    def test_03_records_cancellation(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        self.workflow.cancel(action_id)

        self.assertEqual(
            self.events_for(action_id),
            ["proposed", "canceled"]
        )

    def test_04_records_successful_execution(self):
        action_id = self.approved_action()

        result = self.workflow.execute(action_id)

        self.assertEqual(result["status"], "completed")

        self.assertEqual(
            self.events_for(action_id),
            [
                "proposed",
                "approved",
                "execution_requested",
                "completed"
            ]
        )

        self.writer.assert_called_once_with("Learn Python")

    def test_05_records_writer_failure(self):
        self.writer.side_effect = OSError("Disk failure")
        action_id = self.approved_action()

        with self.assertRaises(BreakerExecutionError):
            self.workflow.execute(action_id)

        self.assertEqual(
            self.events_for(action_id)[-2:],
            ["execution_requested", "failed"]
        )

    def test_06_rejects_unapproved_execution(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        with self.assertRaises(BreakerExecutionError):
            self.workflow.execute(action_id)

        self.writer.assert_not_called()

        self.assertEqual(
            self.events_for(action_id),
            ["proposed", "execution_requested", "failed"]
        )

    def test_07_canceled_action_cannot_execute(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        self.workflow.cancel(action_id)

        with self.assertRaises(BreakerExecutionError):
            self.workflow.execute(action_id)

        self.writer.assert_not_called()

    def test_08_failed_approval_not_recorded_as_approved(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        self.workflow.cancel(action_id)

        with self.assertRaises(ActionApprovalError):
            self.workflow.approve(action_id)

        self.assertEqual(
            self.events_for(action_id),
            ["proposed", "canceled"]
        )

    def test_09_filter_history_by_action(self):
        first = self.propose("Python")
        second = self.propose("Math")

        self.workflow.approve(first["action_id"])

        first_events = self.workflow.get_history(
            first["action_id"]
        )

        second_events = self.workflow.get_history(
            second["action_id"]
        )

        self.assertEqual(len(first_events), 2)
        self.assertEqual(len(second_events), 1)

    def test_10_history_returns_independent_copy(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        history = self.workflow.get_history()
        history[0]["event"] = "completed"

        actual = self.workflow.get_history(action_id)

        self.assertEqual(
            actual[0]["event"],
            "proposed"
        )

    def test_11_events_have_valid_metadata(self):
        self.propose()

        record = self.workflow.get_history()[0]

        self.assertTrue(record["event_id"])
        self.assertTrue(record["action_id"])

        timestamp = datetime.fromisoformat(
            record["timestamp"]
        )

        self.assertIsNotNone(timestamp.tzinfo)

    def test_12_history_does_not_store_memory_content(self):
        secret_content = "A private preference"
        self.propose(secret_content)

        history = self.workflow.get_history()

        self.assertNotIn(
            secret_content,
            str(history)
        )

    def test_13_duplicate_execution_is_recorded_as_failed(self):
        action_id = self.approved_action()

        self.workflow.execute(action_id)

        with self.assertRaises(BreakerExecutionError):
            self.workflow.execute(action_id)

        self.writer.assert_called_once()

        self.assertEqual(
            self.events_for(action_id)[-2:],
            ["execution_requested", "failed"]
        )

    def test_14_canceled_actions_remain_in_history(self):
        proposal = self.propose()
        action_id = proposal["action_id"]

        self.workflow.cancel(action_id)

        history = self.workflow.get_history(action_id)

        self.assertEqual(len(history), 2)

        self.assertEqual(
            history[-1]["event"],
            "canceled"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
