# Optimizer development checkpoint

This checkout contains the CustomTkinter chat application, Settings hub, local
voice workflow, and a limited Breaker Work mode. For the current implementation
and data flows, see [the architecture guide](docs/ARCHITECTURE.md). Setup,
testing, common debugging steps, and extension instructions are in
[the developer guide](docs/DEVELOPER_GUIDE.md).

## Current capabilities

- Organize persistent chats into folders with shared instructions and notes.
- Build bounded model context from recent history and folder knowledge.
- Use Ollama locally or select configured Gemini, Groq, or OpenAI models with
  explicit cloud consent.
- Use explicit local PocketSphinx dictation and optional local speech output.
- Manage folder knowledge, imported documents, provider selection, and voice
  from Settings.
- Enroll a local Breaker passphrase, then preview and approve a folder-scoped
  memory write. No other Breaker action is currently enabled.

Conversation and provider settings use JSON. Searchable memories/documents use
SQLite FTS5. API keys are read from environment variables. Local application
data, including the Breaker credential verifier, is excluded from Git.

## Follow one model request

Start at `chat_ui.send_message()`:

1. The selected user message is persisted through `conversation_data`.
2. `context_engine.build_model_messages()` constructs a snapshot containing
   instructions, references, and bounded history.
3. `request_worker.run_ai_worker()` calls
   `optimizer_core.generate_from_snapshot()` off the GUI thread.
4. `model_providers.generate_messages()` routes the snapshot to the selected
   provider.
5. A thread-safe queue returns the result to `chat_ui.check_ai_results()`, which
   updates widgets on the Tk event loop and saves the response.

## Follow one Breaker action

Start at `BreakerHUD._preview_memory()`. The controller validates and records a
proposal, the HUD displays its normalized content, and the user explicitly
approves or cancels. An approved action runs in `BreakerActionWorker`; the
worker reports through its queue, while the HUD polls and updates status on the
GUI thread. The executor writes the memory to the currently selected chat
folder. Returning to Optimizer destroys the HUD and locks the Breaker screen.

Breaker authentication is local UI access control, not a security boundary
against someone with unrestricted access to the computer or application files.
The verifier stores a salted PBKDF2 hash only. To enroll again after losing the
passphrase, close Optimizer and remove `data/breaker_credentials.json`; this
manual recovery is possible to anyone with file access.

## Validation

Run the complete suite from the repository root:

```powershell
.\venv\optimizer313\Scripts\python.exe -m pytest -q src
```

Tk-based tests skip when a graphical display is unavailable. Tests do not
require cloud API credentials or live model requests.
