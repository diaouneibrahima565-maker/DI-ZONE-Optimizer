"""Preferences for the chat provider. API keys belong in the environment."""

import json
import os
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "settings.json"
PROVIDERS = ("ollama", "gemini", "groq", "openai")
DEFAULT_SETTINGS = {
    "schema_version": 1,
    "active_provider": "ollama",
    "selected_models": {"ollama": "qwen3:1.7b", "gemini": None, "groq": None, "openai": None},
    "cloud_enabled": False,
}


def validate_settings(settings):
    if not isinstance(settings, dict):
        return False
    models = settings.get("selected_models")
    if not isinstance(models, dict) or "ollama" not in models:
        return False
    for provider, model in models.items():
        if provider not in PROVIDERS or (
            model is not None and (not isinstance(model, str) or not model.strip())
        ):
            return False
    active = settings.get("active_provider")
    return (
        type(settings.get("schema_version")) is int
        and settings["schema_version"] == 1
        and active in PROVIDERS
        and type(settings.get("cloud_enabled")) is bool
        and (active == "ollama" or settings["cloud_enabled"])
    )


def load_settings(path=None):
    path = Path(path or SETTINGS_FILE)
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return deepcopy(DEFAULT_SETTINGS)
    if not validate_settings(settings):
        raise ValueError("Invalid Optimizer provider settings.")
    # Older files only have the first three providers.
    settings["selected_models"] = {
        **DEFAULT_SETTINGS["selected_models"],
        **settings["selected_models"],
    }
    return settings


def save_settings(settings, path=None):
    if not validate_settings(settings):
        raise ValueError("Invalid Optimizer provider settings.")
    path = Path(path or SETTINGS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as stream:
            temporary = Path(stream.name)
            json.dump(settings, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def update_model_preference(settings, provider, model, *, allow_cloud=False):
    if provider not in PROVIDERS:
        raise ValueError("Unknown provider.")
    if provider != "ollama" and allow_cloud is not True:
        raise ValueError("Choose whether to send chat context to this cloud provider.")
    if model is not None and not isinstance(model, str):
        raise ValueError("Model ID must be text.")
    updated = deepcopy(settings)
    updated["active_provider"] = provider
    updated["cloud_enabled"] = provider != "ollama"
    updated["selected_models"][provider] = (model or "").strip() or None
    if not validate_settings(updated):
        raise ValueError("Invalid model selection.")
    return updated
