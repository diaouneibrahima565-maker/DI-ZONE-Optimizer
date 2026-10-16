
import unittest
from unittest.mock import Mock, patch

import model_providers


class TestStructuredProviders(unittest.TestCase):

    def setUp(self):
        self.messages = [
            {
                "role": "system",
                "content": "You are Optimizer."
            },
            {
                "role": "user",
                "content": "What is a Python dictionary?"
            },
            {
                "role": "assistant",
                "content": "It stores key-value pairs."
            },
            {
                "role": "user",
                "content": "Can I use it to store conversations?"
            }
        ]

    def test_01_valid_ollama_request(self):
        fake_response = Mock()
        fake_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "Yes, dictionaries can store conversation data."
            }
        }

        with patch(
            "model_providers.requests.post",
            return_value=fake_response
        ) as mock_post:

            result = model_providers.generate_messages(
                self.messages,
                provider_name="ollama"
            )

        self.assertEqual(
            result,
            "Yes, dictionaries can store conversation data."
        )

        mock_post.assert_called_once_with(
            model_providers.OLLAMA_URL,
            json={
                "model": model_providers.OLLAMA_MODEL,
                "messages": self.messages,
                "stream": False,
                "think": False
            },
            timeout=model_providers.OLLAMA_TIMEOUT
        )

    def test_02_invalid_top_level_inputs(self):
        for value in (None, "", {}, 123, []):
            with self.subTest(value=value):
                with self.assertRaises(
                    model_providers.ModelProviderError
                ):
                    model_providers.generate_messages(
                        value,
                        provider_name="ollama"
                    )

    def test_03_invalid_message_structures(self):
        invalid_cases = [
            [123],
            [{}],
            [{"role": "unknown", "content": "Hello"}],
            [{"role": "user", "content": ""}],
            [{"role": "user", "content": "   "}],
            [{"role": "user", "content": 123}],
            [{"role": "user"}],
            [{"content": "Hello"}]
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(
                    model_providers.ModelProviderError
                ):
                    model_providers.generate_messages(
                        case,
                        provider_name="ollama"
                    )

    def test_04_unsupported_provider(self):
        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            model_providers.generate_messages(
                self.messages,
                provider_name="invalid"
            )

    def test_05_missing_ollama_response_message(self):
        fake_response = Mock()
        fake_response.json.return_value = {}

        with patch(
            "model_providers.requests.post",
            return_value=fake_response
        ):
            with self.assertRaises(
                model_providers.ModelProviderError
            ):
                model_providers.generate_messages(
                    self.messages,
                    provider_name="ollama"
                )

    def test_06_unwanted_thinking_markup(self):
        fake_response = Mock()
        fake_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": (
                    "Planning text...</think>"
                    "Here is the answer."
                )
            }
        }

        with patch(
            "model_providers.requests.post",
            return_value=fake_response
        ):
            with self.assertRaises(
                model_providers.ModelProviderError
            ):
                model_providers.generate_messages(
                    self.messages,
                    provider_name="ollama"
                )

    def test_07_local_connection_failure(self):
        import requests

        with patch(
            "model_providers.requests.post",
            side_effect=requests.exceptions.ConnectionError(
                "Simulated connection error"
            )
        ):
            with self.assertRaises(
                model_providers.ModelProviderError
            ):
                model_providers.generate_messages(
                    self.messages,
                    provider_name="ollama"
                )

    def test_08_openai_structured_request(self):
        fake_client = Mock()
        fake_client.responses.create.return_value.output_text = (
            "Yes, you can store conversations in dictionaries."
        )

        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-only-key",
                "OPTIMIZER_OPENAI_MODEL": "gpt-5-mini"
            },
            clear=True
        ):
            with patch(
                "model_providers.OpenAI",
                return_value=fake_client
            ) as mock_client:

                result = model_providers.generate_messages(
                    self.messages,
                    provider_name="openai"
                )

        self.assertEqual(
            result,
            "Yes, you can store conversations in dictionaries."
        )

        mock_client.assert_called_once_with(
            api_key="test-only-key",
            timeout=30.0
        )

        fake_client.responses.create.assert_called_once_with(
            model="gpt-5-mini",
            input=self.messages,
            store=False
        )

    def test_09_openai_missing_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(
                model_providers.ModelProviderError
            ):
                model_providers.generate_messages(
                    self.messages,
                    provider_name="openai"
                )

    def test_10_ollama_does_not_use_openai(self):
        fake_response = Mock()
        fake_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "Local response"
            }
        }

        with patch(
            "model_providers.requests.post",
            return_value=fake_response
        ):
            with patch(
                "model_providers.OpenAI"
            ) as mock_openai:

                result = model_providers.generate_messages(
                    self.messages,
                    provider_name="ollama"
                )

        self.assertEqual(result, "Local response")
        mock_openai.assert_not_called()

    def test_11_input_list_is_not_modified(self):
        original = [
            message.copy()
            for message in self.messages
        ]

        fake_response = Mock()
        fake_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "Answer"
            }
        }

        with patch(
            "model_providers.requests.post",
            return_value=fake_response
        ):
            model_providers.generate_messages(
                self.messages,
                provider_name="ollama"
            )

        self.assertEqual(self.messages, original)

    def test_12_empty_ollama_answer(self):
        fake_response = Mock()
        fake_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "   "
            }
        }

        with patch(
            "model_providers.requests.post",
            return_value=fake_response
        ):
            with self.assertRaises(
                model_providers.ModelProviderError
            ):
                model_providers.generate_messages(
                    self.messages,
                    provider_name="ollama"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
