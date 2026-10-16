
import os
import unittest
from unittest.mock import patch

import model_providers


class TestModelProviders(unittest.TestCase):

    def setUp(self):
        # Replace the real OpenAI client with a mock.
        patcher = patch("model_providers.OpenAI")

        self.mock_openai = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_client = self.mock_openai.return_value

        self.mock_client.responses.create.return_value.output_text = (
            "Hello from the simulated AI!"
        )

    def run_with_fake_credentials(self, prompt="Hello"):
        # This is a fake key. No real request is made.
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "unit-test-key",
                "OPTIMIZER_OPENAI_MODEL": "gpt-5-mini"
            },
            clear=True
        ):
            return model_providers.openai_generate(prompt)

    def test_01_registry(self):
        self.assertIn("prototype", model_providers.PROVIDERS)
        self.assertIn("openai", model_providers.PROVIDERS)

    def test_02_prototype_is_still_default(self):
        self.assertEqual(
            model_providers.generate_response(
                "Hello",
                provider_name="prototype"
            ),
            model_providers.prototype_generate("Hello")
        )

    def test_03_successful_response(self):
        result = self.run_with_fake_credentials()

        self.assertEqual(
            result,
            "Hello from the simulated AI!"
        )

    def test_04_correct_api_arguments(self):
        self.run_with_fake_credentials(
            "Explain Python dictionaries."
        )

        self.mock_client.responses.create.assert_called_once_with(
            model="gpt-5-mini",
            input="Explain Python dictionaries.",
            store=False
        )

    def test_05_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(
                model_providers.ModelProviderError
            ):
                model_providers.openai_generate("Hello")

        self.mock_openai.assert_not_called()

    def test_06_invalid_prompts(self):
        invalid_prompts = ["", "   ", None, 123]

        for prompt in invalid_prompts:
            with self.subTest(prompt=prompt):
                with self.assertRaises(
                    model_providers.ModelProviderError
                ):
                    self.run_with_fake_credentials(prompt)

        self.mock_openai.assert_not_called()

    def test_07_empty_model_response(self):
        self.mock_client.responses.create.return_value.output_text = "  "

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.run_with_fake_credentials()

    def test_08_network_failure(self):
        self.mock_client.responses.create.side_effect = (
            ConnectionError("Simulated network failure")
        )

        with self.assertRaises(
            model_providers.ModelProviderError
        ):
            self.run_with_fake_credentials()

    def test_09_custom_model_selection(self):
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "unit-test-key",
                "OPTIMIZER_OPENAI_MODEL": "example-model"
            },
            clear=True
        ):
            model_providers.openai_generate("Hello")

        arguments = (
            self.mock_client.responses.create.call_args.kwargs
        )

        self.assertEqual(
            arguments["model"],
            "example-model"
        )

    def test_10_response_whitespace(self):
        self.mock_client.responses.create.return_value.output_text = (
            "   Hello from the model.   "
        )

        result = self.run_with_fake_credentials()

        self.assertEqual(
            result,
            "Hello from the model."
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
