
import unittest

from breaker_actions import BreakerActionError
from breaker_approval import (
    ActionApprovalManager,
    ActionApprovalError
)


class TestActionApprovalManager(unittest.TestCase):

    def setUp(self):
        self.manager = ActionApprovalManager()

    def create_proposal(self, content="Learn Python"):
        return self.manager.propose(
            "memory_write",
            {"content": content}
        )

    def test_01_create_pending_proposal(self):
        proposal = self.create_proposal()

        self.assertEqual(
            proposal["status"],
            "pending_approval"
        )

        self.assertEqual(
            proposal["action_type"],
            "memory_write"
        )

    def test_02_retrieve_proposal(self):
        proposal = self.create_proposal()

        result = self.manager.get_proposal(
            proposal["action_id"]
        )

        self.assertEqual(result, proposal)

    def test_03_approve_pending_proposal(self):
        proposal = self.create_proposal()

        approved = self.manager.approve(
            proposal["action_id"]
        )

        self.assertEqual(
            approved["status"],
            "approved"
        )

        stored = self.manager.get_proposal(
            proposal["action_id"]
        )

        self.assertEqual(stored["status"], "approved")

    def test_04_cancel_pending_proposal(self):
        proposal = self.create_proposal()

        canceled = self.manager.cancel(
            proposal["action_id"]
        )

        self.assertEqual(
            canceled["status"],
            "canceled"
        )

    def test_05_cannot_approve_canceled(self):
        proposal = self.create_proposal()
        action_id = proposal["action_id"]

        self.manager.cancel(action_id)

        with self.assertRaises(ActionApprovalError):
            self.manager.approve(action_id)

        self.assertEqual(
            self.manager.get_proposal(action_id)["status"],
            "canceled"
        )

    def test_06_cannot_cancel_approved(self):
        proposal = self.create_proposal()
        action_id = proposal["action_id"]

        self.manager.approve(action_id)

        with self.assertRaises(ActionApprovalError):
            self.manager.cancel(action_id)

    def test_07_cannot_approve_twice(self):
        proposal = self.create_proposal()
        action_id = proposal["action_id"]

        self.manager.approve(action_id)

        with self.assertRaises(ActionApprovalError):
            self.manager.approve(action_id)

    def test_08_cannot_cancel_twice(self):
        proposal = self.create_proposal()
        action_id = proposal["action_id"]

        self.manager.cancel(action_id)

        with self.assertRaises(ActionApprovalError):
            self.manager.cancel(action_id)

    def test_09_unknown_action_rejected(self):
        for method in (
            self.manager.get_proposal,
            self.manager.approve,
            self.manager.cancel
        ):
            with self.subTest(method=method.__name__):
                with self.assertRaises(
                    ActionApprovalError
                ):
                    method("unknown_action")

    def test_10_invalid_action_ids(self):
        for invalid in (None, "", "   ", 123):
            with self.subTest(action_id=invalid):
                with self.assertRaises(
                    ActionApprovalError
                ):
                    self.manager.get_proposal(invalid)

    def test_11_external_changes_do_not_affect_storage(self):
        proposal = self.create_proposal()
        action_id = proposal["action_id"]

        proposal["status"] = "approved"
        proposal["action_data"]["content"] = "Changed"

        stored = self.manager.get_proposal(action_id)

        self.assertEqual(
            stored["status"],
            "pending_approval"
        )

        self.assertEqual(
            stored["action_data"]["content"],
            "Learn Python"
        )

    def test_12_retrieved_copy_is_independent(self):
        proposal = self.create_proposal()
        action_id = proposal["action_id"]

        retrieved = self.manager.get_proposal(action_id)

        retrieved["status"] = "canceled"

        self.assertEqual(
            self.manager.get_proposal(action_id)["status"],
            "pending_approval"
        )

    def test_13_invalid_proposal_rejected(self):
        with self.assertRaises(BreakerActionError):
            self.manager.propose(
                "delete_file",
                {"content": "Example"}
            )

    def test_14_unique_independent_actions(self):
        first = self.create_proposal("Python")
        second = self.create_proposal("Mathematics")

        self.assertNotEqual(
            first["action_id"],
            second["action_id"]
        )

        self.manager.approve(first["action_id"])

        self.assertEqual(
            self.manager.get_proposal(
                second["action_id"]
            )["status"],
            "pending_approval"
        )

    def test_15_original_input_unchanged(self):
        original_data = {
            "content": "  Learn Python  "
        }

        proposal = self.manager.propose(
            "memory_write",
            original_data
        )

        self.assertEqual(
            original_data["content"],
            "  Learn Python  "
        )

        self.assertEqual(
            proposal["action_data"]["content"],
            "Learn Python"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
