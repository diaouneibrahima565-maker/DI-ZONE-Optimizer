
import unittest

from breaker_actions import (
    BreakerActionError,
    create_action_proposal
)


class TestBreakerActions(unittest.TestCase):

    def test_01_valid_proposal(self):
        proposal = create_action_proposal(
            "memory_write",
            {"content": "Learn Python"}
        )

        self.assertEqual(
            proposal["action_type"],
            "memory_write"
        )

        self.assertEqual(
            proposal["status"],
            "pending_approval"
        )

        self.assertEqual(
            proposal["action_data"]["content"],
            "Learn Python"
        )

    def test_02_invalid_action_type(self):
        with self.assertRaises(BreakerActionError):
            create_action_proposal(
                "delete_file",
                {"content": "Example"}
            )

    def test_03_empty_action_type(self):
        with self.assertRaises(BreakerActionError):
            create_action_proposal(
                "   ",
                {"content": "Example"}
            )

    def test_04_invalid_action_data(self):
        with self.assertRaises(BreakerActionError):
            create_action_proposal(
                "memory_write",
                None
            )

    def test_05_empty_memory_content(self):
        with self.assertRaises(BreakerActionError):
            create_action_proposal(
                "memory_write",
                {"content": "   "}
            )

    def test_06_independent_data_copy(self):
        original = {"content": "Learn Python"}

        proposal = create_action_proposal(
            "memory_write",
            original
        )

        proposal["action_data"]["content"] = "Changed"

        self.assertEqual(
            original["content"],
            "Learn Python"
        )

    def test_07_unique_action_ids(self):
        first = create_action_proposal(
            "memory_write",
            {"content": "Python"}
        )

        second = create_action_proposal(
            "memory_write",
            {"content": "Mathematics"}
        )

        self.assertNotEqual(
            first["action_id"],
            second["action_id"]
        )

    def test_08_content_normalization(self):
        proposal = create_action_proposal(
            " memory_write ",
            {"content": "  Learn Python  "}
        )

        self.assertEqual(
            proposal["action_type"],
            "memory_write"
        )

        self.assertEqual(
            proposal["action_data"]["content"],
            "Learn Python"
        )

    def test_09_reject_extra_fields(self):
        with self.assertRaises(BreakerActionError):
            create_action_proposal(
                "memory_write",
                {
                    "content": "Learn Python",
                    "execute": True
                }
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
