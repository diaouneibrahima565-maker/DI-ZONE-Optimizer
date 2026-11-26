# DI-ZONE Optimizer Architecture

## Overview

Optimizer is a single-process Python desktop application. CustomTkinter owns the
one root window and all GUI callbacks run on its Tk event loop. The UI calls
small data/service modules; potentially slow AI and voice work is performed
outside the event loop and reported back through queues or scheduled callbacks.

```text
src/main.py
  ├── chat_ui.py ── backend_controls.py ── settings_data.py
  │       │                    ├────────── model_providers.py
  │       │                    ├────────── voice_io.py (child process)
  │       │                    └────────── action_tools.py / knowledge_store.py
  │       ├── context_engine.py ────────── conversation_data.py
  │       │                    └────────── knowledge_store.py
  │       └── request_worker.py ── optimizer_core.py ── model_providers.py
  ├── breaker_auth.py
  └── breaker_hud.py ── breaker_controller.py ── breaker_workflow.py
                          ├── breaker_approval.py
                          ├── breaker_execution.py ── knowledge_store.py
                          └── breaker_worker.py
```

`ui_theme.py` holds shared palette values. `ui_icons.py` draws the small
composer icons locally with Pillow; it adds no icon-package dependency.

## Startup and navigation

`main.main()` selects the dark CustomTkinter appearance, loads conversation
data, creates one `CTk` root, then constructs `OptimizerApplication`. The
application creates a fixed header, a shared view container, and the chat view.
Chat remains mounted while hidden so switching screens does not discard its
conversation display or request lifecycle.

The header opens Settings or Breaker access. Breaker access first shows an
enrollment or unlock form. Returning to Optimizer destroys the access form or
Breaker HUD; destroying the HUD cancels any unapproved proposal and stops its
GUI callbacks. The current root is never replaced.

## Chat, model requests, and threads

`chat_ui.show_chat_interface()` builds the folder sidebar, conversation
display, and composer. Folder and conversation selection updates the shared
selection in `conversation_data`. Creating a folder or conversation updates
that module's in-memory data and persists it to JSON.

On Send:

1. `chat_ui.send_message()` validates the current conversation and saves the
   user message.
2. `context_engine.build_model_messages()` combines base instructions, folder
   instructions, folder notes, retrieved references, a short recap, and recent
   messages. It returns a request snapshot.
3. The UI captures the selected provider and model, starts a request in
   `RequestLifecycle`, and launches `run_ai_worker()` on a daemon thread.
4. `optimizer_core.generate_from_snapshot()` sends the snapshot to
   `model_providers.generate_messages()`.
5. The worker places a result dictionary in a thread-safe `queue.Queue`.
   `chat_ui.check_ai_results()` polls that queue with `after()`, validates the
   request ID, persists the response, updates widgets on the Tk thread, then
   finishes the request.

The provider/model are captured before the worker starts. Changing Settings
while generation is in progress therefore affects the next request, not the
already-running snapshot.

## Models and Settings

`settings_data.py` validates and atomically saves the selected provider,
configured model IDs, and cloud-consent flag in `data/settings.json`.
Credentials for cloud services are read from environment variables by
`model_providers.py`; they are not saved in application settings.

The compact composer selector only offers provider/model pairs that are
already configured. Settings can configure a model or discover installed
Ollama models. Selecting a cloud model asks for consent before changing the
active provider. Remote model IDs must be valid for the user's provider
account; provider errors are shown in chat if a remote account rejects a model.

## Voice dictation and speech

The microphone button explicitly starts one `voice_io.py listen` subprocess.
`voice_io.dictate()` uses the existing SpeechRecognition/PocketSphinx path,
which performs offline dictation; it does not transmit audio to a cloud
service. `BackendControls` waits for the child process on a background thread,
then uses `after()` to update the composer on the GUI thread. The microphone
button changes to Stop while listening. The Settings hub also retains the
existing stop and optional spoken-reply controls.

Spoken replies use the existing local `voice_io.py speak` operation. Audio
errors are surfaced in a warning instead of being silently ignored.

## Breaker access, approval, and execution

`breaker_auth.py` creates a random salt and derives a password hash with
PBKDF2-HMAC-SHA256. Only the salt, KDF identifier, fixed iteration count, and
hash are stored in `data/breaker_credentials.json`; the plaintext passphrase
is never written or logged. Verification compares derived hashes with
`hmac.compare_digest`. Five consecutive failed unlocks trigger a short,
in-memory exponential delay capped at five minutes.

After unlock, `main.py` creates a `BreakerController` whose memory writer saves
to the currently selected Optimizer folder. Breaker presently supports only a
memory write; other tools and AI work are not exposed as functional actions.

```text
User enters memory text
    → Preview creates a normalized proposal
    → user reviews exact text
    → Approve starts BreakerActionWorker
    → controller approves and executes the proposal
    → local knowledge store writes the memory
    → worker queues a result for the HUD
    → HUD updates status and reactor state
```

`breaker_actions.py` validates proposals, `breaker_approval.py` enforces
pending/approved/canceled states, `breaker_execution.py` rejects execution
unless approval was granted, and `breaker_workflow.py` records lifecycle
events. The non-daemon Breaker worker never updates widgets. The HUD polls its
result queue on the Tk thread.

The reactor remains the `Canvas` animation in `breaker_hud.py`. Its
state-dependent rotation, color, resize geometry, scheduled callback, and
destroy cleanup are separate from the added navigation button.

### Authentication limitations and recovery

Breaker locks whenever the user returns to Optimizer or closes the process.
The failed-attempt delay is held in memory and restarts with a new application
process. This is local UI access control, not a security boundary: a person
with unrestricted control of the computer, Python process, or application
files can bypass it or replace the credential file.

There is no password-reset back door. To enroll a new passphrase, close the
application and manually remove `data/breaker_credentials.json`; the next
Breaker visit will request a new enrollment. This recovery also means someone
with access to the application files can reset the local gate.

## Data storage

| Data | Module | Location | Purpose |
|---|---|---|---|
| Folders, chats, messages, instructions, simple notes | `conversation_data.py` | `data/conversations.json` | Chat history and folder context |
| Provider/model preferences | `settings_data.py` | `data/settings.json` | Active provider, configured models, cloud opt-in |
| Searchable memories and imported text | `knowledge_store.py` | `data/knowledge.sqlite3` | Folder-scoped SQLite FTS5 index |
| Breaker passphrase verifier | `breaker_auth.py` | `data/breaker_credentials.json` | Salted password hash only |
| Cloud API keys | `model_providers.py` | Environment variables | Credentials are not persisted by Optimizer |

`data/` is excluded by `.gitignore`; local conversations and credentials must
not be committed.

## Safe feature extension

Keep UI event handlers short and place reusable state changes in the module
that owns the data. Use the existing data validation and persistence helpers.
For slow work, capture the inputs before starting a worker, never touch a Tk
widget from that worker, send a result through a queue, and apply it from an
`after()` callback. For Breaker actions, add validation, preview, approval,
execution, and tests before exposing a new action in the HUD. Do not treat
authentication as authorization for a destructive action: every action still
needs its explicit approval.
