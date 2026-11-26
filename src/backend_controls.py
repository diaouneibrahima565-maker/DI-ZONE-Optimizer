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
import customtkinter
from action_tools import run_plan
from ui_theme import (
    BACKGROUND,
    BORDER,
    ELEVATED_SURFACE,
    PRIMARY,
    SECONDARY,
    SECONDARY_TEXT,
    SURFACE,
    TEXT,
)

ERRORS = (OSError, ValueError, sqlite3.Error)


def selected_chat():
    selection = conversation_data.ACTIVE_SELECTION
    return selection["folder_id"], selection["conversation_id"]


class BackendControls:
    def __init__(
        self,
        parent,
        entry,
        status_label=None,
        microphone_button=None,
        microphone_icon=None,
        open_breaker_callback=None,
    ):
        self.parent = parent
        self.entry = entry
        self.audio = None
        self.closed = False
        self.microphone_button = microphone_button
        self.microphone_icon = microphone_icon
        self.open_breaker_callback = open_breaker_callback
        self.spoken_replies = tk.BooleanVar(master=parent, value=False)
        try:
            self.settings = settings_data.load_settings()
        except (OSError, ValueError) as error:
            self.settings = deepcopy(settings_data.DEFAULT_SETTINGS)
            messagebox.showwarning(
                "Provider settings", f"{error} Using Ollama for this session.", parent=parent
            )

        self.status = status_label or ttk.Label(parent)
        self.model_selector = None
        self._model_labels = {}

    def attach_model_selector(self, selector):
        self.model_selector = selector
        self._refresh_model_selector()

    def model_options(self):
        """Return only provider/model pairs already configured by the user."""
        options = {}
        for provider in settings_data.PROVIDERS:
            model = self.settings["selected_models"].get(provider)
            if isinstance(model, str) and model.strip():
                options[f"{provider.upper()} · {model}"] = (provider, model)
        return options

    def _refresh_model_selector(self):
        if self.model_selector is None:
            return
        options = self.model_options()
        self._model_labels = options
        labels = list(options)
        self.model_selector.configure(values=labels or ["Configure a model in Settings"])
        active_provider = self.settings["active_provider"]
        active_model = self.settings["selected_models"].get(active_provider)
        active_label = next(
            (
                label for label, selection in options.items()
                if selection == (active_provider, active_model)
            ),
            "Configure a model in Settings",
        )
        self.model_selector.set(active_label)
        self.model_selector.configure(state="normal" if labels else "disabled")

    def select_model(self, label):
        selection = self._model_labels.get(label)
        if selection is None:
            self._refresh_model_selector()
            return
        provider, model = selection
        allowed = provider == "ollama" or messagebox.askyesno(
            "Use cloud provider?",
            f"Send future chat context and retrieved folder notes to {provider}? "
            "Your account may be billed.",
            parent=self.parent,
        )
        if not allowed:
            self._refresh_model_selector()
            return
        try:
            updated = settings_data.update_model_preference(
                self.settings, provider, model, allow_cloud=allowed
            )
            settings_data.save_settings(updated)
        except ERRORS as error:
            messagebox.showerror("Settings", str(error), parent=self.parent)
            self._refresh_model_selector()
            return
        self.settings = updated
        self._refresh_model_selector()

    def open_settings(self):
        """Show the modern settings hub while reusing existing backend features."""
        window = customtkinter.CTkToplevel(self.parent)
        window.title("Optimizer Settings")
        window.geometry("520x600")
        window.configure(fg_color=BACKGROUND)
        window.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            window,
            text="Settings",
            text_color=TEXT,
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(22, 4))
        customtkinter.CTkLabel(
            window,
            text="Models, voice, folder knowledge and tools",
            text_color=SECONDARY_TEXT,
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 16))

        actions = (
            ("General", "Keep the application on its dark green theme.",
             self._keep_dark_appearance),
            ("AI Models", "Choose a provider, configure a model, or discover Ollama models.",
             self.provider_dialog),
            ("Knowledge & Tools", "Manage folder notes, search memory, and import documents.",
             self.tools_dialog),
            ("Voice", "Start offline dictation or stop active audio.",
             self._open_voice_settings),
            ("Breaker", "Unlock the permission-controlled Work workspace.",
             self._open_breaker),
        )
        for row, (title, description, command) in enumerate(actions, start=2):
            card = customtkinter.CTkFrame(
                window, fg_color=SURFACE, corner_radius=12,
                border_color=BORDER, border_width=1,
            )
            card.grid(row=row, column=0, sticky="ew", padx=20, pady=6)
            card.grid_columnconfigure(0, weight=1)
            customtkinter.CTkLabel(
                card, text=title, text_color=PRIMARY,
                font=("Segoe UI", 15, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
            customtkinter.CTkLabel(
                card, text=description, text_color=SECONDARY_TEXT,
                wraplength=310, justify="left",
            ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))
            customtkinter.CTkButton(
                card, text="Open", command=command,
                fg_color=ELEVATED_SURFACE, hover_color=SECONDARY,
                text_color=TEXT, width=76,
            ).grid(row=0, column=1, rowspan=2, padx=12)

        customtkinter.CTkCheckBox(
            window,
            text="Read new replies aloud",
            variable=self.spoken_replies,
            text_color=TEXT,
            fg_color=SECONDARY,
            hover_color=PRIMARY,
        ).grid(row=7, column=0, sticky="w", padx=24, pady=(14, 8))
        customtkinter.CTkButton(
            window,
            text="Stop microphone or speech",
            command=self.stop,
            fg_color="transparent",
            hover_color=ELEVATED_SURFACE,
            text_color=SECONDARY_TEXT,
        ).grid(row=8, column=0, sticky="e", padx=20, pady=(2, 18))
        window.transient(self.parent.winfo_toplevel())

    def _open_voice_settings(self):
        if selected_chat()[1] is None:
            messagebox.showinfo("Voice", "Select a conversation first.", parent=self.parent)
            return
        self.start_audio("listen")

    @staticmethod
    def _keep_dark_appearance():
        customtkinter.set_appearance_mode("Dark")

    def _open_breaker(self):
        if self.open_breaker_callback is None:
            messagebox.showinfo(
                "Breaker", "Open Breaker from the application header.", parent=self.parent
            )
            return
        self.open_breaker_callback()

    def provider_dialog(self):
        window = customtkinter.CTkToplevel(self.parent)
        window.title("Model provider")
        window.configure(fg_color=BACKGROUND)
        provider = tk.StringVar(window, self.settings["active_provider"])
        model = tk.StringVar(window)
        customtkinter.CTkLabel(
            window, text="Provider", text_color=TEXT
        ).pack(anchor="w", padx=16, pady=(16, 2))
        choices = customtkinter.CTkOptionMenu(
            window, variable=provider, values=list(settings_data.PROVIDERS),
            command=lambda selected_provider: update_fields(selected_provider),
            fg_color=ELEVATED_SURFACE, button_color=SECONDARY,
            button_hover_color=PRIMARY, text_color=TEXT,
        )
        choices.pack(fill="x", padx=16, pady=4)
        customtkinter.CTkLabel(
            window, text="Model ID", text_color=TEXT
        ).pack(anchor="w", padx=16, pady=(8, 2))
        models = customtkinter.CTkComboBox(
            window, variable=model, values=(), fg_color=SURFACE,
            border_color=BORDER, text_color=TEXT, button_color=SECONDARY,
            button_hover_color=PRIMARY,
        )
        models.pack(fill="x", padx=16, pady=4)

        def update_fields(selected_provider=None):
            name = selected_provider or provider.get()
            model.set(self.settings["selected_models"].get(name) or "")
            discover.configure(state="normal" if name == "ollama" else "disabled")

        def discover_models():
            try:
                available_models = model_providers.list_ollama_models()
                models.configure(values=available_models)
                if available_models:
                    model.set(available_models[0])
                else:
                    messagebox.showinfo(
                        "Ollama", "No installed Ollama models were found.", parent=window
                    )
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
            self._refresh_model_selector()
            window.destroy()

        discover = customtkinter.CTkButton(
            window, text="List installed Ollama models",
            command=discover_models, fg_color=ELEVATED_SURFACE,
            hover_color=SECONDARY, text_color=TEXT,
        )
        discover.pack(padx=12, pady=4)
        update_fields()
        customtkinter.CTkButton(
            window, text="Save", command=save,
            fg_color=PRIMARY, hover_color=SECONDARY, text_color=BACKGROUND,
        ).pack(padx=12, pady=(8, 16))
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
        if operation == "listen" and self.microphone_button is not None:
            self.microphone_button.configure(text="Stop", image=None, command=self.stop)

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
            self._reset_microphone_button()
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

    def _reset_microphone_button(self):
        if self.microphone_button is not None and not self.closed:
            self.microphone_button.configure(
                text="", image=self.microphone_icon, command=self.dictate
            )

    def stop(self):
        if self.audio is not None:
            if self.audio.poll() is None:
                self.audio.terminate()
            self.audio = None
            if not self.closed:
                self.status.configure(text="")
                self._reset_microphone_button()

    def close(self):
        self.closed = True
        self.stop()
