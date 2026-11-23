import logging
import optimizer_core
from model_providers import ModelProviderError


logger = logging.getLogger(__name__)


def run_ai_worker(
    request_id,
    folder_id,
    conversation_id,
    provider_name,
    model_messages,
    result_queue,
    generate_reply = None,
    model = None
):
    """
    Generate an AI response in a background worker.

    This function never updates GUI widgets.
    Results are returned through a thread-safe queue.
    """

    if generate_reply is None:
        generate_reply = optimizer_core.generate_from_snapshot

    try:
        if model is None:
            response = generate_reply(model_messages, provider_name=provider_name)
        else:
            response = generate_reply(model_messages, provider_name=provider_name, model=model)

        result = {
            "request_id": request_id,
            "folder_id": folder_id,
            "conversation_id": conversation_id,
            "status": "success",
            "response": response
        }

    except ModelProviderError as error:
        result = {
            "request_id": request_id, "folder_id": folder_id, "conversation_id": conversation_id,
            "status": "error", "response": str(error),
        }

    except Exception:
        logger.exception("AI generation failed.")

        result = {
            "request_id": request_id,
            "folder_id": folder_id,
            "conversation_id": conversation_id,
            "status": "error",
            "response": "AI generation failed. Please try again."
        }

    result_queue.put(result)
