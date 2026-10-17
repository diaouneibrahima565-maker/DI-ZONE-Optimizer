
import unittest
from unittest.mock import patch

import optimizer_core
import model_providers


class TestOptimizerSnapshot(unittest.TestCase):

    def setUp(self):
        self.messages = [
            {
                "role": "system",
                "content": "You are Optimizer."
            },
            {
                "role": "user",
                "content": "What is a Python dictionary?"
            }
        ]

        patcher = patch(
            "optimizer_core.model_providers.generate_messages"
        )

        self.mock_provider = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_provider.return_value = (
            "A dictionary stores key-value pairs."
        )

    def generate(self, messages=None, provider="ollama"):
        if messages is None:
            messages = self.messages

        return optimizer_core.generate_from_snapshot(
            messages,
            provider_name=provider
        )

    def test_01_successful_generation(self):
        response = self.generate()

        self.assertEqual(
            response,
            "A dictionary stores key-value pairs."
        )

    def test_02_ollama_routing(self):
        self.generate()

        self.assertEqual(
            self.mock_provider.call_args.kwargs["provider_name"],
            "ollama"
        )

    def test_03_openai_routing(self):
        self.generate(provider="openai")

        self.assertEqual(
            self.mock_provider.call_args.kwargs["provider_name"],
            "openai"
        )

    def test_04_invalid_snapshot_type(self):
        for value in (None, {}, "hello", 123):
            with self.subTest(value=value):
                with self.assertRaises(
                    model_providers.ModelProviderError
                ):
                    optimizer_core.generate_from_snapshot(value)

        self.mock_provider.assert_not_called()

    def test_05_empty_snapshot(self):
        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.generate(messages=[])

        self.mock_provider.assert_not_called()

    def test_06_invalid_provider(self):
        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.generate(provider="unknown")

        self.mock_provider.assert_not_called()

    def test_07_last_message_must_be_user(self):
        invalid_messages = [
            {
                "role": "system",
                "content": "You are Optimizer."
            },
            {
                "role": "assistant",
                "content": "Hello!"
            }
        ]

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.generate(messages=invalid_messages)

        self.mock_provider.assert_not_called()

    def test_08_malformed_final_message(self):
        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.generate(messages=[None])

        self.mock_provider.assert_not_called()

    def test_09_provider_receives_snapshot(self):
        self.generate()

        args, kwargs = self.mock_provider.call_args

        self.assertEqual(args[0], self.messages)
        self.assertEqual(kwargs["provider_name"], "ollama")

    def test_10_snapshot_is_deep_copied(self):
        self.generate()

        sent_messages = self.mock_provider.call_args.args[0]

        self.assertEqual(sent_messages, self.messages)
        self.assertIsNot(sent_messages, self.messages)
        self.assertIsNot(sent_messages[0], self.messages[0])
        self.assertIsNot(sent_messages[1], self.messages[1])

    def test_11_provider_mutation_does_not_change_original(self):

        def simulated_provider(messages, provider_name):
            messages[1]["content"] = "Modified by provider"
            return "Response"

        self.mock_provider.side_effect = simulated_provider

        response = self.generate()

        self.assertEqual(response, "Response")
        self.assertEqual(
            self.messages[1]["content"],
            "What is a Python dictionary?"
        )

    def test_12_provider_error_propagates(self):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
