# DI-ZONE Optimizer

**Version:** 0.1.0 — Foundation Release
**Development branch:** Backend checkpoint through v0.5.0. Breaker v0.6.0 is next.

[Backend checkpoint, examples and next coding task](BACKEND_CHECKPOINT.md)

**Language:** Python
**Framework:** CustomTkinter
**AI Architecture:** Local-first, hybrid cloud-ready

---

## Overview

**DI-ZONE Optimizer (Opt)** is a modular desktop AI assistant developed in Python as part of the DI-ZONE ecosystem.

Optimizer is designed to assist with programming, education, research, problem-solving, and everyday tasks.

Its long-term purpose is to evolve into a general-purpose personal AI system capable of combining language models, knowledge, memory, reasoning, and user-authorized tools.

**Version 0.1.0 establishes Optimizer's first functional AI foundation.**

The application can manage independent conversations, apply folder-specific instructions and knowledge, communicate with a local language model through Ollama, and display AI responses inside a graphical desktop interface.

The first version emphasizes modularity, local execution, and extensibility.

---

## Features — v0.1.0

### 1. Desktop Chat Interface

Optimizer provides a graphical chat interface built using CustomTkinter.

Implemented features include:

- Dark-themed desktop interface.
- Sidebar navigation.
- Conversation selection.
- User and AI message displays.
- Persistent conversation histories.
- AI-generation status indicator.
- Responsive interface during background model inference.

### 2. Folder and Conversation Management

Conversations can be organized into independent folders.

Supported capabilities include:

- Creating folders.
- Creating conversations.
- Selecting conversations.
- Organizing conversations by subject or purpose.
- Maintaining separate message histories.
- Loading saved conversations.

### 3. Shared Folder Instructions

Each folder can contain instructions that influence how the assistant responds.

For example, a programming folder can instruct Optimizer to prioritize technical explanations and implementation guidance.

These instructions become part of the structured context sent to the model.

### 4. Shared Knowledge

Folders can also contain knowledge notes.

Supported operations include:

- Adding notes.
- Viewing stored notes.
- Removing notes.
- Applying shared knowledge to conversations within the folder.

Knowledge notes provide reference information for the local AI model.

### 5. Conversation Context Engine

Optimizer includes a dedicated Context Engine.

It constructs AI requests using:

- Base assistant instructions.
- Folder instructions.
- Shared knowledge.
- Recent conversation messages.
- The latest user request.

Stored conversation roles are converted into the structured format supported by AI providers.

This enables multi-turn conversations rather than isolated single-message interactions.

### 6. Local AI Integration

Optimizer supports local language-model inference through **Ollama**.

**Current default model: Qwen3 1.7B**

The local model was selected after performance testing on a CPU-based development system.

The provider implementation supports:

- Ollama's local HTTP API.
- Structured chat messages.
- Model configuration.
- Request timeouts.
- Response validation.
- Error handling.

Local inference does not require per-request cloud API payments.

### 7. Cloud AI Provider Architecture

The model-provider layer also includes integration with the OpenAI API.

Implemented capabilities include:

- Environment-variable API key configuration.
- Structured message requests.
- API response handling.
- Provider-specific error handling.

On the pre-Breaker branch, open **Backend → Provider and model** to choose Ollama, Gemini, Groq or OpenAI.

Cloud API usage is optional and may incur charges if enabled.

### 8. Asynchronous AI Processing

Optimizer performs model generation using background worker threads.

Implemented mechanisms include:

- Background inference requests.
- Thread-safe response queues.
- Main-thread GUI updates.
- Unique request identifiers.
- Conversation-specific response handling.
- Busy-state management.
- Basic generation-error recovery.

This keeps the desktop interface usable while the local model generates a response.

### 9. Local Data Persistence

The application stores information in JSON format.

Persisted data includes:

- Folders.
- Conversations.
- Messages.
- Folder instructions.
- Knowledge notes.

The data layer includes operations for saving, loading, and validating stored information.

---

## Technology Stack

| Technology        | Purpose                          |
| ----------------- | -------------------------------- |
| Python 3.13       | Core application                 |
| CustomTkinter     | Desktop interface                |
| Tkinter           | Supporting GUI functions         |
| Pillow            | Image assets                     |
| JSON              | Chat and model preferences       |
| SQLite FTS5       | Folder memory and document search |
| Requests          | Ollama HTTP communication        |
| Ollama            | Local model runtime              |
| Qwen3 1.7B        | Default local AI model           |
| OpenAI Python SDK | Optional cloud model integration |
| Threading         | Background inference             |
| Queue             | Thread-safe communication        |
| unittest          | Automated testing                |
| Git / GitHub      | Version control                  |

---

## Project Structure

```text
DI-ZONE Optimizer/
│
├── README.md
├── BACKEND_CHECKPOINT.md
├── requirements-voice.txt
├── .gitignore
│
├── assets/
│   └── optimizer_brain_circuit_white.png
│
├── data/
│   ├── conversations.json
│   ├── settings.json
│   └── knowledge.sqlite3
│
└── src/
    ├── main.py
    ├── chat_ui.py
    ├── optimizer_core.py
    ├── model_providers.py
    ├── context_engine.py
    ├── conversation_data.py
    │
    ├── settings_data.py
    ├── knowledge_store.py
    ├── action_tools.py
    ├── backend_controls.py
    ├── voice_io.py
    ├── test_pre_breaker.py
    ├── test_converdsation_data.py
    ├── test_context_engine.py
    ├── test_model_providers.py
    ├── test_ollama_provider.py
    ├── test_structured_providers.py
    └── test_optimizer_core.py
```

_Local conversation data is excluded from Git version control._

---

## Installation

### Windows laptop check with Python 3.13

From the project root in a Windows VS Code terminal, run `.\check-laptop.cmd`. It creates or reuses `venv\optimizer313`, installs the app, test and voice packages, then runs the suite. It sends a short test message to the standard local Ollama model, starting the installed server if needed. It asks before downloading a missing model or using the microphone. The terminal prints a result for each check.

To launch Optimizer in the same environment, run `.\venv\optimizer313\Scripts\python.exe src\main.py`. You can also select that interpreter in VS Code.

### Ubuntu or WSL 2

From the checkout, run `bash run-ubuntu.sh` to open Optimizer. On first launch it installs the app packages in a Linux virtual environment. It prefers Ubuntu's Python 3.13 and otherwise uses `python3`. The Windows installation of Python is separate. If the distro's Python needs Tk or venv, install them with `sudo apt update && sudo apt install python3-tk python3-venv`. For a separately installed interpreter, use its matching Tk and venv packages.

Run `bash run-ubuntu.sh --check` for the project tests, local Ollama request and optional voice check. After setup, `bash run-ubuntu.sh --recheck` retries just Ollama, speaker playback and microphone dictation. Each failure includes its reason in the final summary. For voice on Ubuntu, install `build-essential python3-dev portaudio19-dev espeak-ng alsa-utils libasound2-plugins` with apt first. Use matching Python development headers if you selected a different interpreter than the distro default.

In WSL, try `curl -fsS http://127.0.0.1:11434/api/tags`. A JSON response means an Ollama server is reachable. With mirrored networking this can be the existing Windows server. If Ubuntu cannot reach loopback directly, the launcher also probes the Windows loopback address using `curl.exe`. Open Ollama from the Windows Start menu before launching or rechecking. If needed, start Ollama inside Ubuntu. The checker can start an installed Linux Ollama and offers to download the project's model if it is missing. See [Ollama for Linux](https://docs.ollama.com/linux) and [WSL networking](https://learn.microsoft.com/windows/wsl/networking).

### Requirements

- Python 3.13 or a compatible version.
- Ollama.
- Python project dependencies.

### 1. Clone the Repository

```bash
git clone https://github.com/diaouneibrahima565-maker/DI-ZONE-Optimizer.git
cd DI-ZONE-Optimizer
```

To try this checkpoint before it lands on main, run `git switch backend/pre-breaker`.

### 2. Install Dependencies

```powershell
python -m pip install customtkinter pillow requests openai
```

### 3. Install Ollama

Download Ollama from:

[https://ollama.com](https://ollama.com)

### 4. Download the Local Model

```powershell
ollama pull qwen3:1.7b
```

Verify:

```powershell
ollama list
```

Ensure Ollama is running before starting Optimizer.

### 5. Launch the Application

```powershell
python src/main.py
```

Create or select a conversation and send a message.

### Optional cloud and voice settings

Ollama is selected on first launch. To use a cloud provider, set its API key in your environment, choose the provider and model under **Backend → Provider and model**, then confirm. The variables are `GEMINI_API_KEY`, `GROQ_API_KEY` and `OPENAI_API_KEY`. Use a model ID your account can access.

To enable offline English dictation and spoken replies, install the optional audio packages in the same Python environment as Optimizer:

```powershell
python -m pip install -r requirements-voice.txt
```

## Development and Testing

Run the full suite from the project root, including the existing conversation-data checks:

```powershell
python -m pip install pytest
python -m pytest -q src
```

The test suite is designed to verify:

- JSON data management.
- Folder and conversation operations.
- Context construction.
- Message validation.
- Provider request handling.
- Core response generation.
- Error handling.

Additional automated GUI and concurrency testing is planned.

---

## Development Roadmap

### v0.1.0 — AI Foundation

**Completed functional first version**

- [x] Establish project structure.
- [x] Create CustomTkinter chat interface.
- [x] Implement folder and conversation management.
- [x] Implement JSON persistence.
- [x] Add folder-specific instructions.
- [x] Add shared knowledge notes.
- [x] Build modular model providers.
- [x] Integrate local AI through Ollama.
- [x] Build the Context Engine.
- [x] Integrate context-aware model requests.
- [x] Implement background AI processing.
- [x] Display real AI responses in the GUI.
- [x] Support consecutive local AI messages.

### v0.1.x — Reliability and Interface Refinement

- [x] Expand asynchronous reliability tests.
- [x] Improve immutable request-context handling.
- [x] Strengthen conversation isolation.
- [x] Improve shutdown and error recovery.
- [x] Add GUI provider selection.
- [ ] Improve inference performance.
- [ ] Refine AI response presentation.

### v0.2.0 — Memory Engine

- Persistent assistant memory.
- More advanced context organization.
- Conversation summarization.
- Memory retrieval and management.
- Token-budget optimization.

### v0.3.0 — Knowledge Engine

- Document-based knowledge.
- Information retrieval.
- Research assistance.
- Knowledge organization and indexing.

### v0.4.0 — Agent Engine

- Modular action tools.
- Permission-controlled operations.
- User confirmation for sensitive actions.
- Multi-step task execution.

### v0.5.0 — Voice Interaction

- Speech recognition.
- Voice-based commands.
- Spoken responses.
- Voice conversation workflows.

### v0.6.0 — Breaker Mode

Breaker Mode is a planned advanced interaction environment inspired by intelligent personal computer assistants.

Its goals include voice-first interaction, authorized computer automation, and deeper DI-ZONE integration.

### Long-Term Goals

- Hybrid local/cloud AI orchestration.
- Advanced reasoning and planning.
- Multimodal interaction.
- Robotics and simulation integrations.
- Stronger security and permission systems.
- Exploration of independently developed AI models, including **1-Plasma**.

Breaker is the next development milestone. Work on 1-Plasma follows Breaker.

---

## DI-ZONE Ecosystem

Optimizer is intended to become the central AI assistant within the broader DI-ZONE ecosystem.

Potential integrations include:

- **DI-ZONE HUB** — Application launcher and dashboard.
- **DI-ZONE Student** — Academic management.
- **DI-ZONE Robot Simulator** — Future robotics and simulation environment.

Integration with these modules will be developed incrementally.

---

## What I Am Learning

Developing Optimizer has helped me gain experience with:

- Python application architecture.
- Desktop interface development.
- CustomTkinter.
- Modular programming.
- API communication.
- Local language-model integration.
- AI provider abstractions.
- Conversation-context construction.
- JSON storage and validation.
- Multithreading.
- Thread-safe queues.
- Exception handling.
- Mock-based unit testing.
- Debugging and performance optimization.
- Git and GitHub.

## Development Philosophy

DI-ZONE Optimizer follows an incremental development approach.

Each release should establish reliable functionality before expanding the assistant's capabilities.

The system is intended to remain modular and maintain clear boundaries between the user interface, AI models, knowledge, memory, and tools.

**The goal is to create an extensible personal AI assistant that increases user capability while preserving user control.**

## License

No open-source license has been selected. All rights are reserved unless a license is added.

---

**DI-ZONE Optimizer — The AI foundation of the DI-ZONE ecosystem.**
