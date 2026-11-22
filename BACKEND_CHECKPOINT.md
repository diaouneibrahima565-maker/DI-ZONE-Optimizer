# Optimizer backend checkpoint

**Resume with v0.6.0 Breaker Mode.** The last published foundation commit was `70f1ee4` on October 17, 2026. This branch implements the pre-Breaker backend through the README’s v0.5.0 voice milestone. The version numbers describe roadmap milestones. The branch does not create release tags.

| Milestone | What you can do now | Start reading in |
| --- | --- | --- |
| v0.1.x · Model selection | Choose an installed Ollama model or explicitly enable Gemini, Groq or OpenAI. Optimizer saves your choice between launches. | [settings_data.py](src/settings_data.py), [model_providers.py](src/model_providers.py) |
| v0.2.0 · Memory | Save, list and forget memories in a folder. A new conversation in the same folder can recall them. Long chats include short excerpts from earlier turns. | [context_engine.py](src/context_engine.py), [knowledge_store.py](src/knowledge_store.py) |
| v0.3.0 · Knowledge | Import UTF-8 Markdown or text files up to 1 MiB. Search their excerpts by keyword or ask a question in the folder. Re-import a changed file to refresh it. | [knowledge_store.py](src/knowledge_store.py) |
| v0.4.0 · Actions | Write one or more steps using `remember`, `search` and `forget`. Inspect and confirm the plan. If a later step fails, earlier edits roll back. | [action_tools.py](src/action_tools.py) |
| v0.5.0 · Voice | Dictate an English draft, edit and send it, or use it as a tool step. Enable spoken replies for the session. Stop releases the audio process. | [voice_io.py](src/voice_io.py), [backend_controls.py](src/backend_controls.py) |

## Follow one message

Start in [context_engine.py](src/context_engine.py) at `build_model_messages`. A chat turn starts with a folder ID, a conversation ID and a question.

1. The context engine reads the selected conversation. It looks up relevant local memories and document excerpts using the latest question.
2. It builds a list of dictionaries with `role` and `content`. The list contains folder instructions, bounded reference text and the most recent turns. Older turns contribute short first-sentence excerpts. Budgets use character counts as a model-independent approximation. The newest user turn stays intact.
3. [request_worker.py](src/request_worker.py) sends that snapshot to the selected provider. The UI associates the reply with the original conversation, even if you switch chats.

JSON holds conversations and model preferences. SQLite holds searchable memories and documents. The default is local Ollama. Cloud confirmation covers future messages and their retrieved reference text until you switch providers. API keys come from the environment.

## Try it in two chats

1. Open a conversation and choose **Backend → Folder knowledge and tools**. Enter the two lines below, choose **Review plan**, and confirm.

   ```text
   remember The telescope uses a cobalt filter.
   search telescope
   ```

2. Open a second conversation in the same folder and ask “Which filter does the telescope use?” The matching memory is included in the request. A different folder has its own index entries.
3. To use voice, install the optional dependencies in the README. Choose **Backend → Dictate one message** and say “remember the telescope uses a blue filter.” Review the draft. Open **Folder knowledge and tools → Use chat draft → Review plan** to run it. For ordinary conversation, use Send. **Stop microphone or speech** ends the current audio operation.

## First Breaker task

Build **one user-approved Breaker turn inside Optimizer**. Start with a selected folder and a typed or dictated draft. Show the action preview, let the user approve or cancel it, and record the result in a visible activity history. Reuse `run_plan` for the first tool and the existing voice controls for input and Stop. The first acceptance check is that cancelling a proposed memory write leaves the folder unchanged and records the cancellation. Add broader desktop actions in later steps. Work on 1-Plasma comes after Breaker.
