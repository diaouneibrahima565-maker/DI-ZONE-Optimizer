
import unittest
from unittest.mock import patch, Mock

import requests
import model_providers


class TestOllamaProvider(unittest.TestCase):

    def setUp(self):
        self.patcher = patch("model_providers.requests.post")
        self.mock_post = self.patcher.start()
        self.addCleanup(self.patcher.stop)

        self.mock_response = Mock()

        self.mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "Hello from local Optimizer!"
            }
        }

        self.mock_post.return_value = self.mock_response

    def test_01_provider_registered(self):
        self.assertIn(
            "ollama",
            model_providers.PROVIDERS
        )

        self.assertIs(
            model_providers.PROVIDERS["ollama"],
            model_providers.ollama_generate
        )

    def test_02_successful_generation(self):
        result = model_providers.ollama_generate("Hello")

        self.assertEqual(
            result,
            "Hello from local Optimizer!"
        )

    def test_03_correct_request(self):
        model_providers.ollama_generate(
            "Explain Python lists."
        )

        self.mock_post.assert_called_once_with(
            model_providers.OLLAMA_URL,
            json={
                "model": model_providers.OLLAMA_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": "Explain Python lists."
                    }
                ],
                "stream": False,
                "think": False
            },
            timeout=model_providers.OLLAMA_TIMEOUT
        )

    def test_04_invalid_prompts(self):
        for prompt in ("", "   ", None, 123):
            with self.subTest(prompt=prompt):
                with self.assertRaises(
                    model_providers.ModelProviderError
                ):
                    model_providers.ollama_generate(prompt)

        self.mock_post.assert_not_called()

    def test_05_connection_failure(self):
        self.mock_post.side_effect = (
            requests.exceptions.ConnectionError(
                "Simulated server unavailable"
            )
        )

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            model_providers.ollama_generate("Hello")

    def test_06_timeout(self):
        self.mock_post.side_effect = (
            requests.exceptions.Timeout(
                "Simulated timeout"
            )
        )

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            model_providers.ollama_generate("Hello")

    def test_07_http_error(self):
        self.mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError(
                "Simulated missing model"
            )
        )

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            model_providers.ollama_generate("Hello")

    def test_08_invalid_json(self):
        self.mock_response.json.side_effect = ValueError(
            "Invalid JSON"
        )

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            model_providers.ollama_generate("Hello")

    def test_09_missing_message(self):
        self.mock_response.json.return_value = {}

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            model_providers.ollama_generate("Hello")

    def test_10_empty_content(self):
        self.mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "   "
            }
        }

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            model_providers.ollama_generate("Hello")

    def test_11_response_whitespace(self):
        self.mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "  Local AI is ready.  "
            }
        }

        result = model_providers.ollama_generate("Hello")

        self.assertEqual(
            result,
            "Local AI is ready."
        )

    def test_12_registry_routing(self):
        result = model_providers.generate_response(
            "Hello",
            provider_name="ollama"
        )

        self.assertEqual(
            result,
            "Hello from local Optimizer!"
        )

        self.mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
