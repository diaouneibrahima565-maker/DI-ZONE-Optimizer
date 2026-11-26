"""Application startup and top-level screen navigation."""

from pathlib import Path
from tkinter import messagebox

from PIL import Image
import customtkinter

import chat_ui
import conversation_data
import knowledge_store
from breaker_auth import (
    AuthenticationThrottle,
    BreakerCredentialStore,
    CredentialStoreError,
)
from breaker_controller import BreakerController
from breaker_hud import BreakerHUD
from ui_theme import (
    BACKGROUND,
    BORDER,
    ELEVATED_SURFACE,
    PRIMARY,
    SECONDARY,
    SIDEBAR,
    TEXT,
    SECONDARY_TEXT,
    SURFACE,
)


class OptimizerApplication:
    """Own the single root window and switch between chat and Breaker screens."""

    def __init__(self, root):
        self.root = root
        self.root.title("DI-ZONE Optimizer")
        self.root.geometry("1200x750")
        self.root.minsize(860, 560)
        self.root.configure(fg_color=BACKGROUND)

        self.credential_store = BreakerCredentialStore()
        self.authentication_throttle = AuthenticationThrottle()
        self.access_view = None
        self.breaker_view = None

        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self._build_header()
        self.view_container = customtkinter.CTkFrame(
            self.root, fg_color=BACKGROUND, corner_radius=0
        )
        self.view_container.grid(row=1, column=0, sticky="nsew")
        self.view_container.grid_rowconfigure(0, weight=1)
        self.view_container.grid_columnconfigure(0, weight=1)

        self.chat_host = customtkinter.CTkFrame(
            self.view_container, fg_color=BACKGROUND, corner_radius=0
        )
        self.chat_host.grid(row=0, column=0, sticky="nsew")
        self.chat_host.grid_rowconfigure(0, weight=1)
        self.chat_host.grid_columnconfigure(0, weight=1)
        self.backend_controls = chat_ui.show_chat_interface(
            self.chat_host, on_open_breaker=self.show_breaker_access
        )

    def _build_header(self):
        header = customtkinter.CTkFrame(
            self.root,
            fg_color=BACKGROUND,
            corner_radius=0,
            border_color=BORDER,
            border_width=1,
        )
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 0))
        header.grid_columnconfigure(0, weight=1)

        brand_icon = None
        icon_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "optimizer_brain_circuit_white.png"
        )
        try:
            with Image.open(icon_path) as source:
                icon = source.convert("RGBA")
            brand_icon = customtkinter.CTkImage(
                light_image=icon, dark_image=icon, size=(24, 24)
            )
        except OSError as error:
            print(f"Optimizer brand icon unavailable: {error}")

        brand = customtkinter.CTkLabel(
            header,
            text="DI-ZONE Optimizer",
            image=brand_icon,
            compound="left",
            text_color=TEXT,
            font=("Segoe UI", 18, "bold"),
        )
        brand.grid(row=0, column=0, sticky="w", padx=14, pady=10)

        self.breaker_button = customtkinter.CTkButton(
            header,
            text="Breaker",
            command=self.show_breaker_access,
            fg_color=ELEVATED_SURFACE,
            hover_color=SECONDARY,
            text_color=PRIMARY,
            corner_radius=10,
            height=40,
            width=112,
        )
        self.breaker_button.grid(row=0, column=1, padx=(8, 4), pady=8)

        settings_button = customtkinter.CTkButton(
            header,
            text="Settings",
            command=self.open_settings,
            fg_color="transparent",
            hover_color=ELEVATED_SURFACE,
            text_color=SECONDARY_TEXT,
            corner_radius=10,
            height=40,
            width=92,
        )
        settings_button.grid(row=0, column=2, padx=(4, 10), pady=8)

    def open_settings(self):
        """Open the settings hub provided by the existing backend controls."""
        self.backend_controls.open_settings()

    def show_breaker_access(self):
        """Lock chat out of view and request local Breaker authentication."""
        if self.breaker_view is not None:
            return
        self.chat_host.grid_remove()
        if self.access_view is not None:
            self.access_view.destroy()
        self.access_view = customtkinter.CTkFrame(
            self.view_container, fg_color=BACKGROUND, corner_radius=0
        )
        self.access_view.grid(row=0, column=0, sticky="nsew")
        self.access_view.grid_columnconfigure(0, weight=1)
        self.access_view.grid_rowconfigure(0, weight=1)
        self._build_access_form()

    def _build_access_form(self):
        try:
            is_enrolled = self.credential_store.is_enrolled()
        except OSError as error:
            messagebox.showerror("Breaker", str(error), parent=self.root)
            self.show_optimizer()
            return

        card = customtkinter.CTkFrame(
            self.access_view,
            fg_color=SIDEBAR,
            border_color=BORDER,
            border_width=1,
            corner_radius=18,
            width=440,
        )
        card.grid(row=0, column=0, padx=24, pady=24)
        card.grid_columnconfigure(0, weight=1)

        title = customtkinter.CTkLabel(
            card,
            text="BREAKER // SECURE WORKSPACE",
            text_color=PRIMARY,
            font=("Segoe UI", 20, "bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=28, pady=(28, 8))

        instruction = (
            "Create a local passphrase to enroll this device."
            if not is_enrolled
            else "Enter your local passphrase to unlock Breaker."
        )
        customtkinter.CTkLabel(
            card,
            text=instruction,
            text_color=SECONDARY_TEXT,
            wraplength=360,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 18))

        password_entry = customtkinter.CTkEntry(
            card,
            placeholder_text="Passphrase",
            show="•",
            height=42,
            fg_color=SURFACE,
            border_color=BORDER,
            text_color=TEXT,
        )
        password_entry.grid(row=2, column=0, sticky="ew", padx=28, pady=6)

        confirmation_entry = None
        if not is_enrolled:
            confirmation_entry = customtkinter.CTkEntry(
                card,
                placeholder_text="Confirm passphrase",
                show="•",
                height=42,
                fg_color=SURFACE,
                border_color=BORDER,
                text_color=TEXT,
            )
            confirmation_entry.grid(row=3, column=0, sticky="ew", padx=28, pady=6)

        status = customtkinter.CTkLabel(
            card, text="", text_color=SECONDARY_TEXT, wraplength=360, justify="left"
        )
        status_row = 4 if confirmation_entry is not None else 3
        status.grid(row=status_row, column=0, sticky="w", padx=28, pady=(8, 2))

        def unlock():
            password = password_entry.get()
            try:
                if is_enrolled:
                    if self.authentication_throttle.remaining_seconds():
                        seconds = self.authentication_throttle.remaining_seconds()
                        status.configure(text=f"Try again in {seconds} seconds.")
                        return
                    authenticated = self.credential_store.verify(password)
                    if not authenticated:
                        seconds = self.authentication_throttle.record_failure()
                        status.configure(
                            text="Passphrase not accepted."
                            if not seconds
                            else f"Passphrase not accepted. Wait {seconds} seconds."
                        )
                        password_entry.delete(0, "end")
                        return
                    self.authentication_throttle.record_success()
                else:
                    if confirmation_entry is None:
                        status.configure(text="Password confirmation is unavailable.")
                        return
                    self.credential_store.enroll(
                        password, confirmation_entry.get()
                    )
            except CredentialStoreError as error:
                status.configure(text=str(error))
                return

            self._open_breaker_workspace()

        unlock_button = customtkinter.CTkButton(
            card,
            text="Unlock Breaker" if is_enrolled else "Enroll and Unlock",
            command=unlock,
            fg_color=PRIMARY,
            hover_color=SECONDARY,
            text_color=BACKGROUND,
            height=42,
            corner_radius=10,
        )
        unlock_button.grid(
            row=status_row + 1,
            column=0,
            sticky="ew",
            padx=28,
            pady=(12, 8),
        )
        back_button = customtkinter.CTkButton(
            card,
            text="Back to Optimizer",
            command=self.show_optimizer,
            fg_color="transparent",
            hover_color=ELEVATED_SURFACE,
            text_color=SECONDARY_TEXT,
            height=38,
        )
        back_button.grid(
            row=status_row + 2,
            column=0,
            sticky="ew",
            padx=28,
            pady=(0, 24),
        )

        def unlock_on_return(event):
            if event.keysym == "Return":
                unlock()

        password_entry.bind("<Return>", unlock_on_return)
        password_entry.focus_set()

    def _open_breaker_workspace(self):
        if self.access_view is not None:
            self.access_view.destroy()
            self.access_view = None

        folder_id = conversation_data.ACTIVE_SELECTION["folder_id"]

        def save_memory(content):
            with knowledge_store.open_store() as database:
                knowledge_store.remember(database, folder_id, content)
            return True

        controller = BreakerController(save_memory)
        self.breaker_view = BreakerHUD(
            self.view_container,
            controller=controller,
            on_back=self.show_optimizer,
        )
        self.breaker_view.grid(row=0, column=0, sticky="nsew")

    def show_optimizer(self):
        """Return to chat and destroy the Breaker session, locking its screen."""
        if self.access_view is not None:
            self.access_view.destroy()
            self.access_view = None
        if self.breaker_view is not None:
            self.breaker_view.destroy()
            self.breaker_view = None
        self.chat_host.grid()


def load_conversations() -> None:
    """Load saved chat data or initialize the first-launch data file."""
    result = conversation_data.load_data()
    if result == "missing":
        if not conversation_data.save_data():
            raise SystemExit("Could not initialize Optimizer conversation data.")
    elif result not in ("loaded",):
        raise SystemExit("Could not load Optimizer conversation data.")


def main() -> None:
    """Start the single-root CustomTkinter application."""
    customtkinter.set_appearance_mode("Dark")
    load_conversations()
    root = customtkinter.CTk()
    OptimizerApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()
