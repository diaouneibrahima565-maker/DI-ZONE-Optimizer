
import unittest
from unittest.mock import patch

import context_engine


class TestContextEngine(unittest.TestCase):

    def setUp(self):
        self.folder_id = "folder_dizone"
        self.conversation_id = "chat_python"

        self.folder_context = {
            "id": self.folder_id,
            "name": "DI-ZONE Development",
            "instructions": "Explain Python using detailed pseudocode.",
            "knowledge": [
                "Optimizer is a Python application.",
                "Breaker Mode is planned."
            ]
        }

        self.history = [
            {
                "role": "user",
                "content": "What is a dictionary?"
            },
            {
                "role": "optimizer",
                "content": "A dictionary stores key-value pairs."
            },
            {
                "role": "user",
                "content": "Can I use it to store conversations?"
            }
        ]

        patcher_conversation = patch(
            "context_engine.conversation_data.get_conversation"
        )

        patcher_context = patch(
            "context_engine.conversation_data.get_folder_context"
        )

        patcher_messages = patch(
            "context_engine.conversation_data.get_messages"
        )

        self.mock_conversation = patcher_conversation.start()
        self.mock_context = patcher_context.start()
        self.mock_messages = patcher_messages.start()

        self.addCleanup(patcher_conversation.stop)
        self.addCleanup(patcher_context.stop)
        self.addCleanup(patcher_messages.stop)

        self.mock_conversation.return_value = {
            "id": self.conversation_id,
            "title": "Python Learning",
            "messages": self.history
        }

        self.mock_context.return_value = self.folder_context
        self.mock_messages.return_value = self.history

    def build(self, limit=12):
        return context_engine.build_model_messages(
            self.folder_id,
            self.conversation_id,
            limit
        )

    def test_01_valid_context_returns_list(self):
        messages = self.build()

        self.assertIsInstance(messages, list)
        self.assertEqual(len(messages), 5)

    def test_02_system_message(self):
        messages = self.build()

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Optimizer", messages[0]["content"])
        self.assertIn(
            "Explain Python using detailed pseudocode.",
            messages[0]["content"]
        )

    def test_03_folder_knowledge(self):
        messages = self.build()

        self.assertEqual(messages[1]["role"], "user")
        self.assertIn(
            "Optimizer is a Python application.",
            messages[1]["content"]
        )
        self.assertIn(
            "Breaker Mode is planned.",
            messages[1]["content"]
        )

    def test_04_role_conversion(self):
        messages = self.build()

        self.assertEqual(
            [item["role"] for item in messages],
            ["system", "user", "user", "assistant", "user"]
        )

    def test_05_message_content_preserved(self):
        messages = self.build()

        self.assertEqual(
            messages[-1]["content"],
            "Can I use it to store conversations?"
        )

    def test_06_history_limit(self):
        messages = self.build(limit=2)

        self.assertEqual(len(messages), 4)
        self.assertEqual(
            messages[-2]["role"],
            "assistant"
        )
        self.assertEqual(
            messages[-1]["role"],
            "user"
        )

    def test_07_empty_history(self):
        self.mock_messages.return_value = []

        messages = self.build()

        self.assertEqual(len(messages), 2)

    def test_08_empty_folder_context(self):
        self.mock_context.return_value = {
            "id": self.folder_id,
            "name": "DI-ZONE Development",
            "instructions": "",
            "knowledge": []
        }

        messages = self.build()

        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["role"], "system")

    def test_09_invalid_folder_id(self):
        messages = context_engine.build_model_messages(
            None,
            self.conversation_id
        )

        self.assertIsNone(messages)
        self.mock_conversation.assert_not_called()

    def test_10_invalid_conversation_id(self):
        messages = context_engine.build_model_messages(
            self.folder_id,
            ""
        )

        self.assertIsNone(messages)

    def test_11_invalid_history_limits(self):
        for limit in (0, -1, True, None, "12"):
            with self.subTest(limit=limit):
                self.assertIsNone(self.build(limit=limit))

    def test_12_missing_conversation(self):
        self.mock_conversation.return_value = None

        self.assertIsNone(self.build())
        self.mock_messages.assert_not_called()

    def test_13_missing_folder_context(self):
        self.mock_context.return_value = None

        self.assertIsNone(self.build())

    def test_14_missing_message_history(self):
        self.mock_messages.return_value = None

        self.assertIsNone(self.build())

    def test_15_no_mutation_of_saved_messages(self):
        original_roles = [
            item["role"] for item in self.history
        ]

        self.build()

        self.assertEqual(
            [item["role"] for item in self.history],
            original_roles
        )

    def test_16_unknown_roles_are_skipped(self):
        self.mock_messages.return_value = [
            {
                "role": "unknown",
                "content": "Unexpected"
            },
            {
                "role": "user",
                "content": "Valid message"
            }
        ]

        messages = self.build()

        self.assertEqual(messages[-1]["content"], "Valid message")
        self.assertFalse(
            any(
                item["content"] == "Unexpected"
                for item in messages
            )
        )

    def test_17_folder_and_chat_identity(self):
        self.build()

        self.mock_conversation.assert_called_once_with(
            self.folder_id,
            self.conversation_id
        )

        self.mock_context.assert_called_once_with(
            self.folder_id
        )

        self.mock_messages.assert_called_once_with(
            self.folder_id,
            self.conversation_id
        )

    def test_18_selected_conversation(self):
        with patch.dict(
            context_engine.conversation_data.ACTIVE_SELECTION,
            {
                "folder_id": self.folder_id,
                "conversation_id": self.conversation_id
            },
            clear=True
        ):
            messages = context_engine.get_selected_model_messages()

        self.assertIsNotNone(messages)
        self.assertEqual(
            messages[-1]["content"],
            "Can I use it to store conversations?"
        )

    def test_19_no_selected_conversation(self):
        with patch.dict(
            context_engine.conversation_data.ACTIVE_SELECTION,
            {
                "folder_id": "folder_general",
                "conversation_id": None
            },
            clear=True
        ):
            messages = context_engine.get_selected_model_messages()

        self.assertIsNone(messages)
        self.mock_conversation.assert_not_called()

    def test_20_other_folder_isolation(self):
        with patch(
            "context_engine.conversation_data.get_conversation",
            return_value=None
        ):
            result = context_engine.build_model_messages(
                "folder_school",
                self.conversation_id
            )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
