import model_providers
import context_engine

def process_message(user_message):
    if not isinstance(user_message, str):
        print("Check if your message is a string.")
        return False

    cleaned_message = user_message.strip()

    if not cleaned_message:
        print('Input message in message entry.')
        return

    response = model_providers.generate_response(prompt = cleaned_message, provider_name = "prototype")

    return response

def generate_conversation_reply(
        folder_id,
        conversation_id,
        provider_name = "ollama"
):
    if not isinstance(folder_id, str) or not folder_id.strip():
        raise model_providers.ModelProviderError("Invalid folder ID.")

    if not isinstance(conversation_id, str) or not conversation_id.strip():
        raise model_providers.ModelProviderError("Invalid conversation ID.")

    folder_id = folder_id.strip()
    conversation_id = conversation_id.strip()

    if provider_name not in ("ollama", "openai"):
        raise model_providers.ModelProviderError("Unsupported conversation provider.")

    model_messages = context_engine.build_model_messages(
        folder_id,
        conversation_id
    )

    if not isinstance(model_messages, list) or not model_messages:
        raise model_providers.ModelProviderError("Could not build conversation context.")

    last_message = model_messages[-1]

    if not isinstance(last_message, dict) or last_message.get("role") != "user":
        raise model_providers.ModelProviderError("Conversation must end with a user message.")

    response = model_providers.generate_messages(
        model_messages,
        provider_name = provider_name
    )

    return response