# DI-ZONE Optimizer Developer Guide

This guide describes the current code, not planned integrations. Breaker
currently exposes one permission-controlled local memory-write action.

## Development setup

### Windows

From the repository root, run:

```powershell
.\run-windows.cmd
```

The launcher creates or reuses `venv\optimizer313`, checks for core GUI/model
packages, and runs `src\main.py`. To launch directly after setup:

```powershell
.\venv\optimizer313\Scripts\python.exe -X utf8 src\main.py
```

The Windows VS Code task can also start the application. Start Ollama locally
for local model requests. Cloud provider credentials are optional and should
be supplied as environment variables, never added to source or JSON settings.

### Ubuntu or WSL

Run `bash run-ubuntu.sh`. It creates a user-local environment and checks that
Tk and a graphical display are available. For Ubuntu setup checks use
`bash run-ubuntu.sh --check`.

Optional offline voice packages are listed in `requirements-voice.txt`:

```powershell
.\venv\optimizer313\Scripts\python.exe -m pip install -r requirements-voice.txt
```

Voice dictation is explicitly initiated and uses PocketSphinx locally.

## Running tests

From the repository root:

```powershell
.\venv\optimizer313\Scripts\python.exe -m pytest -q src
```

The Breaker HUD tests create a real Tk window and skip when no graphical
display is available. The chat/request, data, provider, authentication, and
workflow tests can run without a live AI provider; most provider calls use
mocks.

## Finding your way around

- `src/main.py`: application startup, shared root, top-level screens,
  authentication form, and navigation.
- `src/chat_ui.py`: conversation sidebar, message display, composer, and
  asynchronous request orchestration.
- `src/backend_controls.py`: Settings hub, provider/model configuration,
  folder knowledge/tools dialogs, and voice subprocess lifecycle.
- `src/conversation_data.py`: JSON-backed folders, conversations, and messages.
- `src/context_engine.py`: model context construction and history trimming.
- `src/optimizer_core.py`: request validation and provider dispatch.
- `src/model_providers.py`: Ollama and optional cloud-provider requests.
- `src/request_worker.py` and `src/request_lifecycle.py`: request thread output
  and UI lifecycle state.
- `src/voice_io.py`: offline dictation and local spoken replies.
- `src/knowledge_store.py`: folder-scoped SQLite FTS5 memory and documents.
- `src/breaker_auth.py`: local password hashing, verification, and throttling.
- `src/breaker_hud.py`: Breaker interface, reactor canvas, action controls, and
  result polling.
- `src/breaker_actions.py`, `breaker_approval.py`, `breaker_execution.py`,
  `breaker_workflow.py`, and `breaker_controller.py`: proposal-to-execution
  boundary and event history.
- `src/breaker_worker.py`: the non-daemon worker for approved actions.
- `src/ui_theme.py` and `src/ui_icons.py`: shared colors and composer icons.

## Debugging common errors

1. **Ollama is unavailable:** Start Ollama and confirm it is listening locally.
   In Settings, discover installed models. A request failure is displayed in
   chat; provider code wraps connection and response errors as
   `ModelProviderError`.
2. **A cloud provider fails:** Configure the API key in the process
   environment, choose a model ID allowed by that account, and confirm the
   cloud-use prompt. Do not paste API keys into logs, source, or settings JSON.
3. **Dictation does not start:** Install `requirements-voice.txt`, check the
   microphone permission/device, select a conversation, and try again. The
   UI displays child-process errors. Press Stop to release an active capture.
4. **Conversation data cannot load:** `main.load_conversations()` stops startup
   rather than replacing invalid JSON with blank history. Inspect the local
   `data/conversations.json` backup before attempting recovery.
5. **Breaker will not unlock:** Confirm the passphrase. Repeated failures
   trigger a temporary delay. If the local verifier is corrupted or the
   passphrase is lost, close Optimizer and remove
   `data/breaker_credentials.json` to enroll again. This is not a secure
   recovery boundary against a person with file access.
6. **A widget update fails after navigation:** Check that the callback runs on
   the Tk thread and that its owning frame still exists. Do not update GUI
   objects from a worker thread.

## Add a GUI button

1. Find the owning frame in `chat_ui.show_chat_interface()` or
   `BreakerHUD._build_*()`.
2. Create the CustomTkinter button with the shared colors from `ui_theme.py`.
3. Place it with `.grid()` in that parent (do not mix `.grid()` and `.pack()`
   for children of the same parent).
4. Give it a small callback that validates inputs and calls the existing
   service/data helper.
5. Surface failures with the existing UI error pattern.
6. Add a focused test for behavior that can be tested without a display; run
   the HUD tests for layout/callback changes.

The app's only `CTk()` root is created in `main.main()`. Use `CTkFrame` or
`CTkToplevel` for other screens and dialogs.

## Add a settings option

Use the Settings hub in `BackendControls.open_settings()`. Persist durable
preferences through `settings_data.py` rather than a widget variable or a
second settings file. Validate new values when loading and saving. If a
setting affects an in-flight model request, capture it before starting the
worker so later UI changes apply only to later requests.

## Add a model/provider configuration

1. Add provider/model validation and defaults in `settings_data.py`.
2. Add dispatch and provider-specific error handling in `model_providers.py`.
3. Keep credentials in environment variables; never save API keys to
   `data/settings.json`.
4. Reuse the cloud-consent prompt before sending context outside the machine.
5. Add mock-based tests that prove provider routing, model selection, request
   validation, and error handling without live credentials.
6. Keep the selector limited to models configured through Settings or
   discovered from the local Ollama installation.

## Extend Breaker with an approved action

1. Add strict input validation in `breaker_actions.py`.
2. Make the preview show the exact normalized action and data that will run.
3. Add an approval state transition in `breaker_approval.py`.
4. Add a single-purpose executor in `breaker_execution.py` that refuses
   unapproved or repeated execution.
5. Route it through `breaker_workflow.py` and `breaker_controller.py`, with
   lifecycle events.
6. Run execution with `BreakerActionWorker`; return results through its queue
   and update HUD widgets only in the polling callback.
7. Add tests for invalid input, no approval, cancellation, success, failure,
   duplicate execution, and worker shutdown before adding the UI control.

Authentication only opens the local Breaker screen. It does not replace the
approval check for an action and does not protect the app files from someone
with unrestricted access to the computer.

## Learning sequence

Study one lesson per session. Trace the named functions in order, then try the
exercise before reading the next lesson.

### Lesson 1 — Application startup

**Intuition:** startup is the small sequence that prepares saved state, creates
the one root window, then hands off to the UI.

**Trace:** `main.main()` calls `load_conversations()`, creates
`customtkinter.CTk()`, constructs `OptimizerApplication`, and starts
`root.mainloop()`. `load_conversations()` stops startup if saved data is
invalid; it does not silently replace broken history.

**Concepts and mistake to avoid:** `if __name__ == "__main__"` separates
launching the program from importing a module in a test. Keep startup out of
module-level statements; otherwise importing `main` could create windows.

**Exercise:** find the first-launch branch in `load_conversations()` and
explain why it initializes a missing file but exits on invalid data.

### Lesson 2 — GUI and navigation

**Intuition:** a Tkinter window is a tree of widgets; callbacks respond to
events, and frames let the app replace one view without replacing its root.

**Trace:** `OptimizerApplication._build_header()` places branding and the
Breaker/Settings buttons. `show_breaker_access()` hides `chat_host` and adds
the access view. `show_optimizer()` destroys the protected view and restores
the original chat frame.

**Concepts and mistake to avoid:** `.grid()` controls layout within each
parent; the app has one `CTk()` root and uses frames or `CTkToplevel` for other
surfaces. Do not mix `.grid()` and `.pack()` among children of the same parent.
Several small callbacks inside `show_chat_interface()` are closures: they use
state created by that function, such as `message_row`.

**Exercise:** locate a button's `command` and follow it to the function that
changes the interface.

### Lesson 3 — Chat request flow

**Intuition:** the UI records a turn and snapshots the context; a worker does
the slow request, then the UI thread displays the result.

**Trace:** `chat_ui.send_message()` saves the user message through
`conversation_data.add_message()`, creates context with
`context_engine.build_model_messages()`, captures the provider/model, and
starts `request_worker.run_ai_worker()`. The worker calls
`optimizer_core.generate_from_snapshot()` and puts a result in a thread-safe
queue. `check_ai_results()` polls with `after()`, saves the response, and
updates the widgets on the Tk event loop.

**Concepts and mistake to avoid:** a queue safely transfers data between
threads; it does not make Tk widgets thread-safe. Never call a widget's
`.configure()` from the worker. The request ID and `RequestLifecycle` prevent
stale results from updating the wrong conversation.

**Exercise:** find where the latest user text becomes a model-message
dictionary, and explain why the full context is copied before the request.

### Lesson 4 — Models and providers

**Intuition:** Settings chooses a provider/model pair; the provider module
implements how to communicate with that service.

**Trace:** `BackendControls.select_model()` validates and saves the choice with
`settings_data.update_model_preference()`. The request worker passes the
captured values to `optimizer_core`, which calls
`model_providers.generate_messages()`. That function routes to Ollama, OpenAI,
Gemini, or Groq. Cloud selection requires an explicit consent prompt.

**Concepts and mistake to avoid:** configuration and credentials have
different jobs: model IDs are stored in settings, but API keys come from
environment variables. Never put a key in source code or JSON. A remote
provider may reject a model ID that is not enabled for that account.

**Exercise:** use the provider tests to trace how a selected model reaches the
mock client, without making a real network request.

### Lesson 5 — Voice

**Intuition:** the microphone starts an existing local voice program; the GUI
stays responsive while it listens.

**Trace:** the composer calls `BackendControls.dictate()`. `start_audio()`
launches `voice_io.py listen`, a background thread waits for process output,
and `after()` transfers the transcript into the entry on the Tk thread. The
same controller prevents overlapping audio sessions and provides Stop.

**Concepts and mistake to avoid:** `subprocess.Popen` isolates the optional
audio stack; `communicate()` waits in a worker thread; `after()` is the
main-thread callback mechanism. Dictation uses local PocketSphinx, not a cloud
audio endpoint. Do not start a second listener when `self.audio` is active.

**Exercise:** trace both the success and failure branches in `finish()` and
identify how each restores the microphone button.

### Lesson 6 — Breaker

**Intuition:** Breaker separates a proposed action from permission to perform
it.

**Trace:** `_preview_memory()` asks `BreakerController` for a proposal and
shows its normalized text. Approve starts `BreakerActionWorker`; the
controller/workflow/approval manager mark it approved before the executor
writes to the selected folder's knowledge store. The worker returns a result
through a queue; the HUD updates status and reactor state on the Tk thread.
Cancel or leaving Breaker cancels an unapproved proposal.

**Concepts and mistake to avoid:** the proposal, approval, and execution
states are separate invariants. Authentication does not approve an action.
Do not invoke the executor directly from a preview callback or update the
reactor canvas from the worker.

**Exercise:** follow the cancellation path and identify which component
prevents the memory writer from running.

### Lesson 7 — Authentication and security

**Intuition:** the app saves a verifier for the passphrase, not the passphrase
itself.

**Trace:** `BreakerCredentialStore.enroll()` checks confirmation, creates a
random salt, derives a PBKDF2-HMAC-SHA256 hash, then atomically writes the
verifier. `verify()` derives a candidate and uses constant-time comparison.
`AuthenticationThrottle` adds an in-memory delay after repeated failures.
Returning to Optimizer destroys the HUD; a later entry must unlock again.

**Concepts and mistake to avoid:** hashing is one-way; a salt prevents
precomputed hashes from being reused. The app-owned files remain under the
control of the local computer user, so this is not a security boundary against
someone who can modify the app or delete its verifier.

**Exercise:** inspect a temporary test credential JSON and list which fields
are present; confirm the passphrase itself is not among them.

### Lesson 8 — Extend the application safely

**Intuition:** a feature is easier to maintain when data rules, slow work, and
GUI presentation each stay with their existing owner.

**Trace:** start by finding a nearby feature and its tests. Put validation
beside the data/service operation, call it from a short UI callback, and
update the documentation where users or developers will look for the behavior.
For slow work, snapshot inputs, return results through a queue, and update
widgets on the main thread.

**Concepts and mistake to avoid:** a test should prove a behavior or invariant,
not merely repeat an implementation detail. Avoid new dependencies or
abstractions unless they solve a real problem. For a new Breaker action, add
validation, preview, approval, single-purpose execution, and failure tests
before exposing a button.

**Exercise:** sketch a new read-only Breaker action. List its validated input,
what the preview must display, how approval is checked, and the tests needed
before it can appear in the HUD.
