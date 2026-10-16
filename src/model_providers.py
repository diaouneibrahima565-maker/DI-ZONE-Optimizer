import os
import requests

from openai import OpenAI

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:1.7b"
OLLAMA_TIMEOUT = 120

class ModelProviderError(Exception):
    pass

def ollama_generate(prompt):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ModelProviderError("Prompt must contain text.")

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
            "role": "user",
            "content": prompt
        }
        ],
        "stream": False,
        "think": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json = payload,
            timeout = OLLAMA_TIMEOUT
        )

        response.raise_for_status()

        response_data = response.json()

    except requests.exceptions.RequestException as error:
        raise ModelProviderError("Could not communicate with local Ollama.") from error

    except ValueError as error:
        raise ModelProviderError("Ollama returned invalid JSON.") from error

    if not isinstance(response_data, dict):
        raise ModelProviderError("Unexpected Ollama response.")

    message = response_data.get("message")

    if not isinstance(message, dict):
        raise ModelProviderError("Invalid response structure.")

    content = message.get("content")

    if not isinstance(content, str) or not content.strip():
        raise ModelProviderError("The local model returned no text.")

    return content.strip()

def openai_generate(prompt):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ModelProviderError("Prompt must contain text.")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or not api_key.strip():
        raise ModelProviderError("OPENAI_API_KEY is not configured.")

    model_name = os.getenv(
        "OPTIMIZER_OPENAI_MODEL",
        "gpt-5-mini"
    ).strip() or "gpt-5-mini"

    try:
        client = OpenAI(
            api_key = api_key,
            timeout = 30.0
        )

        response = client.responses.create(
            model = model_name,
            input = prompt,
            store = False
        )

    except Exception as error:
        raise ModelProviderError(
            "OpenAI request failed. "
            "Check your connection and API configuration."
        ) from error

    response_text = response.output_text

    if not isinstance(response_text, str) or not response_text.strip():
        raise ModelProviderError("The model returned no text.")

    response_text = response_text.strip()

    return response_text


def prototype_generate(prompt):
    response = f"[Prototype] Optimizer received: {prompt}"

    return response

PROVIDERS = {
    "prototype": prototype_generate,
    "openai": openai_generate,
    "ollama": ollama_generate
}

def generate_response(prompt, provider_name = "prototype"):
    provider_function = PROVIDERS.get(provider_name)

    if provider_function is None:
        raise ModelProviderError(f"Provider not available: {provider_name}")

    response = provider_function(prompt)

    return response

def ollama_generate_messages(messages):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "think": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json = payload,
            timeout = OLLAMA_TIMEOUT
        )

        response.raise_for_status()

        response_data = response.json()

    except requests.exceptions.RequestException as error:
        raise ModelProviderError(
            f"Could not communicate with local Ollama. "
            f"{type(error).__name__}: {error}"
        ) from error

    except ValueError as error:
        raise ModelProviderError("Ollama returned invalid json.") from error

    if not isinstance(response_data, dict):
        raise ModelProviderError("Unexpected Ollama response.")

    message = response_data.get("message")

    if not isinstance(message, dict):
        raise ModelProviderError("Invalid response structure.")

    content = message.get("content")

    if not isinstance(content, str) or not content.strip():
        raise ModelProviderError("The local model returned no text.")

    if "<think>" in content or "</think>" in content:
        raise ModelProviderError("The local model included unexpected thinking markup.")

    return content.strip()

def openai_generate_messages(messages):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or not api_key.strip():
        raise ModelProviderError("OPENAI_API_KEY is not configured.")

    model_name = os.getenv(
      "OPTIMIZER_OPENAI_MODEL",
      "gpt-5-mini"
    ).strip() or "gpt-5-mini"

    try:
        client = OpenAI(
            api_key = api_key,
            timeout = 30.0
        )

        response = client.responses.create(
            model = model_name,
            input = messages,
            store = False
        )

    except Exception as error:
        raise ModelProviderError("OpenAI request failed.") from error

    response_text = response.output_text

    if not isinstance(response_text, str) or not response_text.strip():
        raise ModelProviderError("The model returned no text.")

    response_text = response_text.strip()

    return response_text

def generate_messages(messages, provider_name = "ollama"):
    if not isinstance(messages, list):
        raise ModelProviderError("Invalid response structure.")

    if not messages:
        raise ModelProviderError("No message stored into messages.")

    for message in messages:
        if not isinstance(message, dict):
            raise ModelProviderError("Message is missing.")

        role = message.get("role")

        content = message.get("content")

        if role not in ("system", "user", "assistant"):
            raise ModelProviderError("Unexpected role.")

        if not isinstance(content, str) or not content.strip():
            raise ModelProviderError("Invalid message content.")

    if provider_name == "ollama":
        return ollama_generate_messages(messages)

    elif provider_name == "openai":
        return openai_generate_messages(messages)

    else:
        raise ModelProviderError("Unsupported structured provider.")