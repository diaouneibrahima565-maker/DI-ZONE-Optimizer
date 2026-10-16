
import unittest
from unittest.mock import patch

import optimizer_core
import model_providers


class TestOptimizerCore(unittest.TestCase):

    def setUp(self):
        self.folder_id = "folder_dizone"
        self.conversation_id = "chat_python"

        self.model_messages = [
            {
                "role": "system",
                "content": "You are Optimizer."
            },
            {
                "role": "user",
                "content": "What is Python?"
            },
            {
                "role": "assistant",
                "content": "Python is a programming language."
            },
            {
                "role": "user",
                "content": "Can I use it to build desktop apps?"
            }
        ]

        context_patcher = patch(
            "optimizer_core.context_engine.build_model_messages"
        )

        provider_patcher = patch(
            "optimizer_core.model_providers.generate_messages"
        )

        self.mock_context = context_patcher.start()
        self.mock_provider = provider_patcher.start()

        self.addCleanup(context_patcher.stop)
        self.addCleanup(provider_patcher.stop)

        self.mock_context.return_value = self.model_messages
        self.mock_provider.return_value = (
            "Yes, Python can build desktop applications."
        )

    def generate(self, provider="ollama"):
        return optimizer_core.generate_conversation_reply(
            self.folder_id,
            self.conversation_id,
            provider_name=provider
        )

    def test_01_successful_generation(self):
        result = self.generate()

        self.assertEqual(
            result,
            "Yes, Python can build desktop applications."
        )

    def test_02_context_arguments(self):
        self.generate()

        self.mock_context.assert_called_once_with(
            self.folder_id,
            self.conversation_id
        )

    def test_03_provider_arguments(self):
        self.generate()

        self.mock_provider.assert_called_once_with(
            self.model_messages,
            provider_name="ollama"
        )

    def test_04_openai_routing(self):
        self.generate(provider="openai")

        self.mock_provider.assert_called_once_with(
            self.model_messages,
            provider_name="openai"
        )

    def test_05_invalid_folder_id(self):
        for value in (None, "", "   ", 123):
            with self.subTest(folder_id=value):
                with self.assertRaises(
                    model_providers.ModelProviderError
                ):
                    optimizer_core.generate_conversation_reply(
                        value,
                        self.conversation_id
                    )

        self.mock_provider.assert_not_called()

    def test_06_invalid_conversation_id(self):
        for value in (None, "", "   ", 123):
            with self.subTest(conversation_id=value):
                with self.assertRaises(
                    model_providers.ModelProviderError
                ):
                    optimizer_core.generate_conversation_reply(
                        self.folder_id,
                        value
                    )

        self.mock_provider.assert_not_called()

    def test_07_invalid_provider(self):
        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.generate(provider="unknown")

        self.mock_provider.assert_not_called()

    def test_08_missing_context(self):
        self.mock_context.return_value = None

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.generate()

        self.mock_provider.assert_not_called()

    def test_09_empty_context(self):
        self.mock_context.return_value = []

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.generate()

        self.mock_provider.assert_not_called()

    def test_10_no_user_message(self):
        self.mock_context.return_value = [
            {
                "role": "system",
                "content": "You are Optimizer."
            }
        ]

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.generate()

        self.mock_provider.assert_not_called()

    def test_11_last_message_is_assistant(self):
        self.mock_context.return_value = [
            {
                "role": "user",
                "content": "Hello"
            },
            {
                "role": "assistant",
                "content": "Hello!"
            }
        ]

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.generate()

        self.mock_provider.assert_not_called()

    def test_12_provider_failure_propagates(self):
        self.mock_provider.side_effect = (
            model_providers.ModelProviderError(
                "Local model unavailable."
            )
        )

        with self.assertRaisesRegex(
            model_providers.ModelProviderError,
            "Local model unavailable"
        ):
            self.generate()

    def test_13_original_ids_are_used(self):
        self.generate()

        self.mock_context.assert_called_once_with(
            "folder_dizone",
            "chat_python"
        )

    def test_14_identifiers_are_trimmed(self):
        optimizer_core.generate_conversation_reply(
            "  folder_dizone  ",
            "  chat_python  "
        )

        self.mock_context.assert_called_once_with(
            "folder_dizone",
            "chat_python"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
