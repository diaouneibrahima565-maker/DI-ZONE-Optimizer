
import unittest
from unittest.mock import Mock

from breaker_approval import ActionApprovalManager
from breaker_execution import (
    MemoryActionExecutor,
    BreakerExecutionError
)


class TestMemoryActionExecutor(unittest.TestCase):

    def setUp(self):
        self.manager = ActionApprovalManager()
        self.writer = Mock(return_value=True)

        self.executor = MemoryActionExecutor(
            self.manager,
            self.writer
        )

    def create_action(self, content="Learn Python"):
        return self.manager.propose(
            "memory_write",
            {"content": content}
        )

    def approve_action(self, content="Learn Python"):
        proposal = self.create_action(content)
        self.manager.approve(proposal["action_id"])
        return proposal["action_id"]

    def test_01_approved_action_executes(self):
        action_id = self.approve_action()

        result = self.executor.execute(action_id)

        self.assertEqual(result["action_id"], action_id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            result["action_type"],
            "memory_write"
        )

        self.writer.assert_called_once_with("Learn Python")

    def test_02_pending_action_is_rejected(self):
        proposal = self.create_action()

        with self.assertRaises(BreakerExecutionError):
            self.executor.execute(proposal["action_id"])

        self.writer.assert_not_called()

    def test_03_canceled_action_is_rejected(self):
        proposal = self.create_action()
        action_id = proposal["action_id"]

        self.manager.cancel(action_id)

        with self.assertRaises(BreakerExecutionError):
            self.executor.execute(action_id)

        self.writer.assert_not_called()

    def test_04_unknown_action_is_rejected(self):
        with self.assertRaises(BreakerExecutionError):
            self.executor.execute("unknown_action")

        self.writer.assert_not_called()

    def test_05_invalid_action_ids(self):
        for invalid_id in (None, "", "   ", 123):
            with self.subTest(action_id=invalid_id):
                with self.assertRaises(BreakerExecutionError):
                    self.executor.execute(invalid_id)

        self.writer.assert_not_called()

    def test_06_cannot_execute_twice(self):
        action_id = self.approve_action()

        self.executor.execute(action_id)

        with self.assertRaises(BreakerExecutionError):
            self.executor.execute(action_id)

        self.writer.assert_called_once()

    def test_07_writer_exception_is_handled(self):
        self.writer.side_effect = OSError(
            "Simulated memory storage failure"
        )

        action_id = self.approve_action()

        with self.assertRaises(BreakerExecutionError):
            self.executor.execute(action_id)

        self.writer.assert_called_once()

        # No automatic second attempt.
        with self.assertRaises(BreakerExecutionError):
            self.executor.execute(action_id)

        self.writer.assert_called_once()

    def test_08_false_confirmation_is_rejected(self):
        self.writer.return_value = False
        action_id = self.approve_action()

        with self.assertRaises(BreakerExecutionError):
            self.executor.execute(action_id)

        with self.assertRaises(BreakerExecutionError):
            self.executor.execute(action_id)

        self.writer.assert_called_once()

    def test_09_none_confirmation_is_rejected(self):
        self.writer.return_value = None
        action_id = self.approve_action()

        with self.assertRaises(BreakerExecutionError):
            self.executor.execute(action_id)

        self.writer.assert_called_once()

    def test_10_multiple_actions_are_independent(self):
        first_id = self.approve_action("Python")
        second_id = self.approve_action("Mathematics")

        first_result = self.executor.execute(first_id)
        second_result = self.executor.execute(second_id)

        self.assertEqual(first_result["status"], "completed")
        self.assertEqual(second_result["status"], "completed")

        self.assertEqual(self.writer.call_count, 2)

        self.writer.assert_any_call("Python")
        self.writer.assert_any_call("Mathematics")

    def test_11_invalid_memory_writer(self):
        with self.assertRaises(BreakerExecutionError):
            MemoryActionExecutor(self.manager, None)

        with self.assertRaises(BreakerExecutionError):
            MemoryActionExecutor(self.manager, "not a function")

    def test_12_invalid_approval_manager(self):
        with self.assertRaises(BreakerExecutionError):
            MemoryActionExecutor(None, self.writer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
