# DI-ZONE Optimizer

**Development status:** v0.6 is implemented. Work on v0.6.1 UI stabilization
is in progress.

The version labels below are project milestones. They are not all published
releases or Git tags.

For more detail, see the [backend checkpoint](BACKEND_CHECKPOINT.md), the
[architecture guide](docs/ARCHITECTURE.md), and the
[developer guide](docs/DEVELOPER_GUIDE.md).

## 1. Project Overview

DI-ZONE Optimizer is a Python desktop assistant that I am developing as a
software engineering learning project. I want to understand how a desktop
application can combine a graphical interface, language-model providers,
local data, background work, and user-approved actions.

Optimizer is the main application. Breaker is an integrated Work mode within
Optimizer, not a separate assistant. The current project focuses on chat,
folder-based knowledge, local and optional cloud models, and a limited,
approval-controlled memory action.

## 2. Current Features

- **Chat and conversations:** Create folders and conversations, switch between
  them, and save messages, folder instructions, and simple knowledge notes as
  JSON data.
- **Conversation context:** Build model requests from folder instructions,
  notes, retrieved references, and a bounded portion of recent history.
- **Model providers:** Use Ollama locally or configure OpenAI, Gemini, or Groq.
  The default local model is `qwen3:1.7b`. Cloud providers require an API key
  in the environment and explicit consent before chat context is sent.
- **Knowledge and tools:** Import `.txt` and `.md` files into a local SQLite
  full-text search index. The folder-scoped tools support `remember`, `search`,
  and `forget` steps after showing the plan and asking for confirmation.
- **Background requests:** Model requests run on worker threads. Results are
  returned through queues and applied to the interface on Tk's event loop.
- **Optional voice:** Dictation uses the local PocketSphinx recognizer. Spoken
  replies use local speech tools. Voice packages and audio devices are
  optional.
- **Settings:** Configure providers and models, start voice features, and open
  Breaker from the shared Settings interface.
- **UI stabilization in progress:** The current development work improves
  wrapping, selection, and scrolling in chat, memory previews, and
  Knowledge & Tools panels. This work is tracked as v0.6.1 and is not described
  here as a released milestone.

Application data is stored locally. Conversation and provider settings use
JSON; searchable memories and imported documents use SQLite with FTS5. Local
data and credentials are excluded from Git.

## 3. Breaker Work Mode

Breaker is a protected workspace inside Optimizer. Its current enabled action
is a folder-scoped memory write:

1. Enter text and preview the normalized content.
2. Review it, then explicitly approve or cancel.
3. If approved, a background worker writes the memory to the selected
   Optimizer folder and reports the result.

The preview, approval state, executor, and worker are separate parts of the
workflow. A pending action is not run just because the user leaves the screen.

Breaker requires a locally enrolled passphrase. The application stores a
salted PBKDF2 hash rather than the passphrase and applies a temporary delay
after repeated failed attempts. This is a local interface gate, not a security
boundary against someone with unrestricted access to the computer, process,
or application files. The delay is held in memory and resets when the
application restarts. Removing `data/breaker_credentials.json` allows a new
local enrollment, so someone with file access can also reset the gate.

Breaker currently has no AI chat, general file operations, arbitrary shell
commands, autonomous computer control, or broad task-execution system. Its
workflow events are held in memory; persistent activity history is proposed
work, not an implemented feature.

## 4. Technologies Used

| Technology | Use |
| --- | --- |
| Python 3.13 | Application language; the Windows launcher requires Python 3.13. The Ubuntu launcher prefers 3.13 and can use the system `python3`. |
| CustomTkinter and Tkinter | Desktop interface and event loop |
| Pillow | Image assets |
| `requests` | Local Ollama HTTP requests |
| OpenAI Python SDK | OpenAI requests and the OpenAI-compatible Gemini and Groq endpoints |
| Ollama | Local model runtime |
| JSON | Conversation data and provider settings |
| SQLite with FTS5 | Folder-scoped searchable memories and imported text |
| `threading`, `queue`, and `subprocess` | Background requests, safe result handoff, and optional voice processes |
| SpeechRecognition with PocketSphinx | Optional offline dictation |
| pyttsx3 and eSpeak NG | Optional local spoken replies, depending on platform |
| `unittest` and `pytest` | Automated tests |
| Git and GitHub | Version control and project hosting |

Cloud API keys are read from environment variables: `OPENAI_API_KEY`,
`GEMINI_API_KEY`, and `GROQ_API_KEY`. Optimizer does not save these keys in its
settings file.

## 5. Project Structure

```text
DI-ZONE-Optimizer/
├── assets/                 # Application images
├── data/                   # Local runtime data; excluded from Git
├── docs/
│   ├── ARCHITECTURE.md
│   └── DEVELOPER_GUIDE.md
├── src/
│   ├── main.py             # Startup, single root window, and navigation
│   ├── chat_ui.py          # Chat interface and request orchestration
│   ├── backend_controls.py # Settings, knowledge tools, and voice controls
│   ├── conversation_data.py # JSON-backed folders, chats, and messages
│   ├── context_engine.py   # Model context construction
│   ├── model_providers.py  # Ollama and cloud-provider requests
│   ├── knowledge_store.py  # SQLite FTS5 memories and documents
│   ├── breaker_*.py        # Breaker access, approval, execution, and worker
│   ├── voice_io.py         # Optional local voice operations
│   └── test_*.py           # Automated tests
├── run-windows.cmd
├── run-ubuntu.sh
├── check-laptop.cmd
├── requirements-voice.txt  # Optional voice dependencies
├── BACKEND_CHECKPOINT.md
└── README.md
```

The `data/` directory is created for local use and is ignored by Git. It can
contain conversation JSON, settings, the SQLite knowledge database, and the
Breaker credential verifier.

## 6. Installation and Setup

### Windows

Clone the repository and open PowerShell in its directory:

```powershell
git clone https://github.com/diaouneibrahima565-maker/DI-ZONE-Optimizer.git
cd DI-ZONE-Optimizer
py -3.13 --version
.\run-windows.cmd
```

The launcher creates or reuses `venv\optimizer313`, checks for the core
packages, and starts the application. Install Ollama separately, start it,
and download the default model:

```powershell
ollama pull qwen3:1.7b
```

To launch directly after setup:

```powershell
.\venv\optimizer313\Scripts\python.exe -X utf8 src\main.py
```

For a machine check, run `.\check-laptop.cmd`. It installs the test and
optional voice packages, runs the project tests, checks for a local Ollama
reply, and offers optional speaker and microphone checks. It may ask before
downloading the model.

To use a cloud provider, set its API key in the process environment, select
the provider and an available model in **Settings → AI Models**, and confirm
the cloud-use prompt. Cloud use may incur charges.

### Ubuntu or WSL

The launcher prefers `python3.13`, otherwise it uses `python3`, and creates
its environment under
`${XDG_DATA_HOME:-$HOME/.local/share}/di-zone-optimizer/`. Install Tk and
`venv` for the selected Python. For Ubuntu's system Python, for example:

```bash
sudo apt update
sudo apt install python3-tk python3-venv
bash run-ubuntu.sh
```

If you use a separately installed Python version, install the matching Tk,
`venv`, and (when needed) development-header packages for that version.
On WSL 2, a graphical display must be available. The launcher can use an
Ollama server running on Windows through WSL loopback when it is reachable;
otherwise, start or install Ollama in the environment where Optimizer runs.

The Ubuntu launcher also supports:

```bash
bash run-ubuntu.sh --check
bash run-ubuntu.sh --recheck
```

`--check` runs the project tests and checks Ollama and optional voice
components. It can ask before downloading a missing model or using audio
devices. `--recheck` retries the Ollama and optional audio checks without
repeating the full setup.

Voice is optional. On Ubuntu or WSL, the audio tools may require:

```bash
sudo apt install build-essential python3-dev portaudio19-dev espeak-ng alsa-utils libasound2-plugins
```

Use the development headers that match the Python interpreter selected by the
launcher. To install the Python voice packages manually on Windows, use:

```powershell
.\venv\optimizer313\Scripts\python.exe -m pip install -r requirements-voice.txt
```

## 7. Running Tests

After setting up the Windows environment, run:

```powershell
.\venv\optimizer313\Scripts\python.exe -m pip install pytest
.\venv\optimizer313\Scripts\python.exe -m pytest -q src
```

On Ubuntu or WSL, first run `bash run-ubuntu.sh` once to create the project
environment. Then run the suite with that environment's Python:

```bash
if command -v python3.13 >/dev/null 2>&1; then
    base_python=python3.13
else
    base_python=python3
fi
python_version=$("$base_python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
optimizer_python="$data_home/di-zone-optimizer/venv-$python_version/bin/python"
"$optimizer_python" -m pip install pytest
"$optimizer_python" -m pytest -q src
```

The unit tests use mocks for provider calls and do not require cloud API keys
or a live language model. Tk-based interface tests need a graphical display;
they skip when one is unavailable. The laptop check is separate from the
unit-test command because it also makes a live local Ollama request and can
test audio devices.

## 8. Development Roadmap

These are project milestones, not claims that each version was published as a
release.

### v0.1 — Initial foundation — implemented

- Created the desktop chat interface and initial local-model connection.
- Added folders, conversations, JSON persistence, and basic context handling.

### v0.2–v0.5 — Backend development — implemented across these milestones

- Expanded model-provider routing, context construction, and request
  validation.
- Added folder knowledge, SQLite FTS5 search, and text/Markdown document
  import.
- Added background request workers, saved provider settings, and explicit
  cloud consent.
- Added optional local dictation and spoken replies.
- Added a confirmed `remember` / `search` / `forget` plan for folder knowledge.

### v0.6 — Breaker Work Mode — implemented

- Added the integrated, locally authenticated Breaker workspace.
- Implemented one preview-and-approve memory-write action.

### v0.6.1 — UI stabilization — in progress

- Improve wrapping, resizing, copy, and scrolling in chat, memory previews,
  and Knowledge & Tools.
- Continue checking usability at different window sizes and display scaling.

### v0.6.2 — Proposed

- Add persistent activity history with a clear scope and retention policy.

### v0.7 and later — Proposed

- Explore carefully permissioned AI-assisted tools and integrations.
- Keep actions reviewable, bounded, and tested before exposing them in the UI.

## 9. What I Am Learning

Through this project I am studying:

- Python modules and separation between interface, data, and service code.
- Event-driven desktop interfaces and Tkinter geometry management.
- JSON and SQLite persistence, input validation, and full-text search.
- Model-provider interfaces, API errors, and conversation context.
- Threads, queues, and keeping slow work off the GUI event loop.
- Authentication, authorization, explicit approval, and their limitations.
- Unit testing with mocks, debugging, and maintaining a Git project.

## 10. AI Assistance and Development Transparency

DI-ZONE Optimizer is a personal software engineering and learning project. I
guide its vision, goals, feature requirements, and development direction. I
use AI tools, including GitHub Copilot and ChatGPT, to assist with
implementation, debugging, code review, documentation, and software design.

The automated test files in this repository were generated with AI
assistance. AI-generated code and tests can be incomplete or incorrect, and
passing tests do not prove that the application is free of bugs or that every
feature has been manually verified. I do not claim to have personally written
every line of code or every test. My goal is to understand the software,
improve my programming skills, and become more independent in designing,
debugging, and maintaining it.

## 11. Future Goals

My long-term goal is to keep improving Optimizer as a modular assistant while
keeping users in control of its actions. Possible future work includes
persistent activity history, carefully approved AI-assisted tools, and
integrations with other DI-ZONE projects. These are goals, not current
features.

Developing **1-Plasma** is a long-term research goal. It is not part of the
current Optimizer implementation or the near-term Breaker stabilization work.

## License

No open-source license has been selected. Until one is added, all rights are
reserved.
