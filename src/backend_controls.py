"""Small desktop controls that call the backend from the existing chat window."""

import sqlite3
import subprocess
import sys
import tkinter as tk
from copy import deepcopy
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from tkinter import filedialog, messagebox, ttk

import conversation_data
import knowledge_store
import model_providers
import settings_data
from action_tools import run_plan

ERRORS = (OSError, ValueError, sqlite3.Error)


def selected_chat():
    selection = conversation_data.ACTIVE_SELECTION
    return selection["folder_id"], selection["conversation_id"]


class BackendControls:
    def __init__(self, parent, entry):
        self.parent = parent
        self.entry = entry
        self.audio = None
        self.closed = False
        self.spoken_replies = tk.BooleanVar(master=parent, value=False)
        try:
            self.settings = settings_data.load_settings()
        except (OSError, ValueError) as error:
            self.settings = deepcopy(settings_data.DEFAULT_SETTINGS)
            messagebox.showwarning(
                "Provider settings", f"{error} Using Ollama for this session.", parent=parent
            )

        menu = tk.Menu(parent, tearoff=False)
        menu.add_command(label="Provider and model…", command=self.provider_dialog)
        menu.add_command(label="Folder knowledge and tools…", command=self.tools_dialog)
        menu.add_separator()
        menu.add_command(label="Dictate one message", command=self.dictate)
        menu.add_command(label="Stop microphone or speech", command=self.stop)
        menu.add_checkbutton(label="Read new replies aloud", variable=self.spoken_replies)
        bar = ttk.Frame(parent)
        bar.grid(row=0, column=0, sticky="e", padx=20)
        self.status = ttk.Label(bar)
        self.status.pack(side="left")
        ttk.Menubutton(bar, text="Backend", menu=menu).pack(side="left")

    def provider_dialog(self):
        window = tk.Toplevel(self.parent)
        window.title("Model provider")
        provider = tk.StringVar(window, self.settings["active_provider"])
        model = tk.StringVar(window)
        ttk.Label(window, text="Provider").pack(anchor="w", padx=12)
        choices = ttk.Combobox(
            window, textvariable=provider, values=settings_data.PROVIDERS, state="readonly"
        )
        choices.pack(fill="x", padx=12, pady=4)
        ttk.Label(window, text="Model ID").pack(anchor="w", padx=12)
        models = ttk.Combobox(window, textvariable=model, width=36)
        models.pack(fill="x", padx=12, pady=4)

        def update_fields(event=None):
            name = provider.get()
            model.set(self.settings["selected_models"].get(name) or "")
            models.configure(values=())
            discover.configure(state="normal" if name == "ollama" else "disabled")

        def discover_models():
            try:
                models.configure(values=model_providers.list_ollama_models())
                models.focus_set()
                models.event_generate("<Down>")
            except model_providers.ModelProviderError as error:
                messagebox.showerror("Ollama", str(error), parent=window)

        def save():
            name = provider.get()
            allowed = name == "ollama" or messagebox.askyesno(
                "Use cloud provider?",
                f"Send future chat context and retrieved folder notes to {name}? Your account may be billed.",
                parent=window,
            )
            if not allowed:
                return
            try:
                updated = settings_data.update_model_preference(
                    self.settings, name, model.get(), allow_cloud=allowed
                )
                settings_data.save_settings(updated)
            except ERRORS as error:
                messagebox.showerror("Settings", str(error), parent=window)
                return
            self.settings = updated
            window.destroy()

        discover = ttk.Button(window, text="List installed Ollama models", command=discover_models)
        discover.pack(padx=12, pady=4)
        choices.bind("<<ComboboxSelected>>", update_fields)
        update_fields()
        ttk.Button(window, text="Save", command=save).pack(padx=12, pady=8)
        window.transient(self.parent.winfo_toplevel())
        window.grab_set()

    def tools_dialog(self):
        folder, _ = selected_chat()
        if not conversation_data.get_folder(folder):
            return
        window = tk.Toplevel(self.parent)
        window.title("Folder knowledge and tools")
        ttk.Label(window, text=conversation_data.get_folder(folder)["name"]).pack(
            anchor="w", padx=12
        )
        ttk.Label(
            window, text="One step per line: remember TEXT, search WORDS, or forget MEMORY_ID"
        ).pack(padx=12)
        steps = tk.Text(window, width=62, height=5, wrap="word")
        steps.pack(fill="x", padx=12, pady=6)
        output = tk.Text(window, width=62, height=10, wrap="word", state="disabled")

        def show(text):
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.insert("1.0", text)
            output.configure(state="disabled")

        def use_draft():
            draft = self.entry.get().strip()
            if draft:
                steps.delete("1.0", "end")
                steps.insert("1.0", draft)

        def run():
            try:
                show(
                    run_plan(
                        folder,
                        steps.get("1.0", "end"),
                        lambda plan: messagebox.askyesno("Run these steps?", plan, parent=window),
                    )
                )
            except ERRORS as error:
                show(str(error))

        def recall():
            try:
                with knowledge_store.open_store() as db:
                    rows = knowledge_store.list_memories(db, folder)
                show(
                    "\n".join(f"#{row['id']}  {row['content']}" for row in rows)
                    or "No saved memories."
                )
            except ERRORS as error:
                show(str(error))

        def import_file():
            path = filedialog.askopenfilename(
                parent=window, filetypes=[("Text and Markdown", "*.txt *.md")]
            )
            if path:
                try:
                    knowledge_store.import_document(folder, path)
                    show(f"Indexed {Path(path).name} in this folder.")
                except ERRORS as error:
                    show(str(error))

        row = ttk.Frame(window)
        row.pack()
        for title, command in (
            ("Use chat draft", use_draft),
            ("Review plan…", run),
            ("List memories", recall),
            ("Import document…", import_file),
        ):
            ttk.Button(row, text=title, command=command).pack(side="left", padx=4)
        output.pack(fill="both", expand=True, padx=12, pady=8)

    def dictate(self):
        if selected_chat()[1] is None:
            messagebox.showinfo("Voice", "Select a conversation first.", parent=self.parent)
            return
        self.start_audio("listen")

    def read_reply(self, text):
        if self.spoken_replies.get() and self.audio is None:
            self.start_audio("speak", text)

    def start_audio(self, operation, text=""):
        if self.audio is not None or self.closed:
            return
        script = Path(__file__).with_name("voice_io.py")
        try:
            process = subprocess.Popen(
                [sys.executable, "-X", "utf8", str(script), operation],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as error:
            messagebox.showerror("Voice", str(error), parent=self.parent)
            return
        self.audio = process
        target = selected_chat()
        self.status.configure(
            text="Listening…" if operation == "listen" else "Reading reply aloud…"
        )

        result = Queue()

        def wait_for_audio():
            try:
                transcript, error = process.communicate(input=text)
                result.put((transcript.strip(), error.strip(), process.returncode != 0))
            except OSError as error:
                result.put(("", str(error), True))

        Thread(target=wait_for_audio, daemon=True).start()

        def finish():
            if self.closed or self.audio is not process:
                return
            try:
                transcript, error, failed = result.get_nowait()
            except Empty:
                self.parent.after(100, finish)
                return
            self.audio = None
            self.status.configure(text="")
            if failed:
                messagebox.showwarning(
                    "Voice", error or "The audio device was unavailable.", parent=self.parent
                )
            elif operation == "listen" and transcript and target == selected_chat():
                if self.entry.get():
                    self.entry.insert("end", " ")
                self.entry.insert("end", transcript)
                self.entry.focus_set()

        self.parent.after(100, finish)

    def stop(self):
        if self.audio is not None:
            if self.audio.poll() is None:
                self.audio.terminate()
            self.audio = None
            if not self.closed:
                self.status.configure(text="")

    def close(self):
        self.closed = True
        self.stop()
