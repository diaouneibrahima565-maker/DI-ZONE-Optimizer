import math
import customtkinter
import threading
import queue

import context_engine
import conversation_data
from backend_controls import BackendControls
from request_lifecycle import (
    RequestLifecycle,
    RequestLifecycleError,
    REQUEST_GENERATING,
    REQUEST_CLOSED
)
from request_worker import run_ai_worker

from PIL import Image
from pathlib import Path
from uuid import uuid4
from tkinter import Misc, messagebox
from ui_icons import create_icon
from ui_theme import (
    BACKGROUND,
    BORDER,
    ELEVATED_SURFACE,
    PRIMARY,
    SECONDARY,
    SECONDARY_TEXT,
    SIDEBAR,
    SURFACE,
    TEXT,
)
from ui_text import create_read_only_textbox, split_markdown_code_blocks


def show_chat_interface(parent, on_open_breaker=None):
    main_frame = customtkinter.CTkFrame(master=parent, fg_color=BACKGROUND)
    main_frame.grid(row = 0, column = 0, sticky = 'nsew')
    main_frame.grid_columnconfigure(0, weight = 0)
    main_frame.grid_columnconfigure(1, weight = 1)
    main_frame.grid_rowconfigure(0, weight = 1)


    sidebar_frame = customtkinter.CTkFrame(master=main_frame, width=260, corner_radius=0, fg_color=SIDEBAR)
    sidebar_frame.grid(row = 0, column = 0, sticky = 'ns')
    sidebar_frame.grid_propagate(False)
    sidebar_frame.grid_columnconfigure(0, weight = 1)
    sidebar_frame.grid_rowconfigure(2, weight = 1)

    chat_panel = customtkinter.CTkFrame(master=main_frame, fg_color=BACKGROUND, corner_radius=0)
    chat_panel.grid(row = 0, column = 1, sticky = 'nsew')
    chat_panel.grid_columnconfigure(0, weight = 1)
    chat_panel.grid_rowconfigure(1, weight = 1)

    icon_path = (Path(__file__).resolve().parent.parent / "assets" / "optimizer_brain_circuit_white.png")

    optimizer_icon = None

    try:
        with Image.open(icon_path)as source:
            icon_image = source.convert("RGBA")

        optimizer_icon = customtkinter.CTkImage(light_image = icon_image, dark_image = icon_image, size = (26, 26))

    except OSError:
        print("optimizer icon not found. Using fallback icon.")

    title_text = "  Optimizer" if optimizer_icon is not None else "DI-ZONE Optimizer"

    sidebar_title = customtkinter.CTkLabel(master = sidebar_frame,
                                           text = title_text, image = optimizer_icon,
                                           compound = "left", text_color = TEXT,
                                           font = ("Segoe UI", 20, "bold"), fg_color = "transparent")
    sidebar_title.grid(row = 0, column = 0, sticky = "w", padx = 20, pady = 20)

    sidebar_actions = customtkinter.CTkFrame(master = sidebar_frame, fg_color = "transparent")
    sidebar_actions.grid(row = 1, column = 0, sticky = 'ew', padx = 12, pady = (0, 10))
    sidebar_actions.grid_columnconfigure(0, weight = 1)
    sidebar_actions.grid_columnconfigure(1, weight = 1)

    new_folder_button = customtkinter.CTkButton(master=sidebar_actions, text="+ Folder",
                                                fg_color=ELEVATED_SURFACE, hover_color=BORDER,
                                                text_color=TEXT, height=36, corner_radius=8, width=100)
    new_folder_button.grid(row = 0, column = 0, sticky = 'ew', padx = 4, pady = 4)

    new_chat_button = customtkinter.CTkButton(master=sidebar_actions, text="+ New chat",
                                              fg_color=SECONDARY, hover_color=PRIMARY,
                                              text_color=BACKGROUND, height=36, corner_radius=8, width=100)
    new_chat_button.grid(row = 0, column = 1, sticky = 'ew', padx = 4, pady = 4)

    folders_scroll_frame = customtkinter.CTkScrollableFrame(master=sidebar_frame, fg_color=SIDEBAR, corner_radius=0)
    folders_scroll_frame.grid(row = 2, column = 0, sticky = 'nsew', padx = 5)
    folders_scroll_frame.grid_columnconfigure(0, weight = 1)

    folders_container = customtkinter.CTkFrame(master = folders_scroll_frame, fg_color = "transparent")
    folders_container.grid(row = 0, column = 0, sticky = 'ew')
    folders_container.grid_columnconfigure(0, weight = 1)

    title_label = customtkinter.CTkLabel(master = chat_panel, text = "Optimizer", text_color = TEXT,
                                         font = ("Segoe UI", 20, "bold"))
    title_label.grid(row = 0, column = 0, sticky = 'w', padx = 20, pady = 10)

    conversation_frame = customtkinter.CTkScrollableFrame(master = chat_panel, corner_radius = 12, fg_color=BACKGROUND)
    conversation_frame.grid(row = 1, column = 0, sticky = 'nsew', padx = 20, pady = 10)
    conversation_frame.grid_columnconfigure(0, weight = 1)
    conversation_canvas = conversation_frame._parent_canvas

    messages_container = customtkinter.CTkFrame(master = conversation_frame, fg_color = "transparent", corner_radius = 0)
    messages_container.grid(row = 0, column = 0, sticky = "ew")
    messages_container.grid_columnconfigure(0, weight = 1)

    input_frame = customtkinter.CTkFrame(master = chat_panel, corner_radius = 15, fg_color=SURFACE)
    input_frame.grid(row = 2, column = 0, sticky = 'ew', padx = 20, pady = 10)
    input_frame.grid_columnconfigure(0, weight = 1)
    input_frame.grid_columnconfigure(1, weight=0)
    input_frame.grid_columnconfigure(2, weight=0)
    input_frame.grid_columnconfigure(3, weight=0)

    message_entry = customtkinter.CTkEntry(
        master=input_frame,
        placeholder_text="Message Optimizer...",
        fg_color=ELEVATED_SURFACE,
        border_color=BORDER,
        text_color=TEXT,
        placeholder_text_color=SECONDARY_TEXT,
        corner_radius=15,
        height=44,
    )
    message_entry.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=10)

    microphone_icon = create_icon("mic", SECONDARY_TEXT)
    microphone_button = customtkinter.CTkButton(
        master=input_frame,
        text="",
        image=microphone_icon,
        width=40,
        height=40,
        corner_radius=12,
        fg_color="transparent",
        hover_color=ELEVATED_SURFACE,
        text_color=TEXT,
    )
    microphone_button.grid(row=0, column=2, padx=4, pady=10)

    send_icon = create_icon("send", BACKGROUND)
    send_button = customtkinter.CTkButton(
        master=input_frame,
        text="",
        image=send_icon,
        width=42,
        height=42,
        corner_radius=12,
        fg_color=PRIMARY,
        hover_color=SECONDARY,
        text_color=BACKGROUND,
    )
    send_button.grid(row=0, column=3, sticky="e", padx=(4, 12), pady=10)

    voice_status = customtkinter.CTkLabel(
        master=chat_panel, text="", text_color=PRIMARY, font=("Segoe UI", 11)
    )
    voice_status.grid(row=3, column=0, sticky="w", padx=25, pady=(0, 2))

    generating_status = customtkinter.CTkLabel(
        master=chat_panel, text="", text_color=SECONDARY_TEXT, font=("Segoe UI", 12)
    )
    generating_status.grid(row=4, column=0, sticky="w", padx=25, pady=(0, 8))

    backend = BackendControls(
        chat_panel,
        message_entry,
        status_label=voice_status,
        microphone_button=microphone_button,
        microphone_icon=microphone_icon,
        open_breaker_callback=on_open_breaker,
    )

    model_selector = customtkinter.CTkOptionMenu(
        input_frame,
        values=["Configure a model in Settings"],
        command=backend.select_model,
        width=154,
        height=36,
        fg_color=ELEVATED_SURFACE,
        button_color=SECONDARY,
        button_hover_color=PRIMARY,
        text_color=TEXT,
        dropdown_fg_color=SURFACE,
        dropdown_hover_color=ELEVATED_SURFACE,
        dropdown_text_color=TEXT,
        font=("Segoe UI", 11),
    )
    model_selector.grid(row=0, column=1, padx=4, pady=10)
    backend.attach_model_selector(model_selector)
    microphone_button.configure(command=backend.dictate)

    message_row = 0
    message_text_widgets = []

    selected_folder_id = conversation_data.ACTIVE_SELECTION["folder_id"]

    expanded_folder_ids = set()

    settings_window = None

    result_queue = queue.Queue()
    request_lifecycle = RequestLifecycle()

    for folder in conversation_data.get_all_folders():
        expanded_folder_ids.add(folder["id"])

    def message_width(text, maximum_width):
        longest_line = max((len(line) for line in text.split("\n")), default=0)
        return min(maximum_width, max(120, longest_line * 8 + 32))

    def message_height(text, width, code_block=False):
        characters_per_line = max(16, (width - 24) // 8)
        if code_block:
            line_count = max(1, len(text.split("\n")))
        else:
            line_count = sum(
                max(1, math.ceil(len(line) / characters_per_line))
                for line in text.split("\n")
            )
        return min(240, max(54, line_count * 20 + 16))

    def update_message_dimensions(_event=None):
        available_width = conversation_canvas.winfo_width()
        if available_width <= 1:
            return

        maximum_width = max(120, min(680, available_width - 70))
        for textbox, text, code_block in message_text_widgets:
            width = message_width(text, maximum_width)
            height = message_height(text, width, code_block)
            if textbox.cget("width") != width or textbox.cget("height") != height:
                textbox.configure(width=width, height=height)

    def scroll_to_bottom():
        conversation_frame.after_idle(
            lambda: conversation_canvas.yview_moveto(1.0)
        )

    def display_message(text, sender, force_scroll=False):
        nonlocal message_row

        if sender == "user":
            bubble_color = "#173C29"
            message_text_color = TEXT
        elif sender == "optimizer":
            bubble_color = SURFACE
            message_text_color = TEXT

        else:
            bubble_color = ELEVATED_SURFACE
            message_text_color = TEXT

        follow_scroll = force_scroll or conversation_canvas.yview()[1] >= 0.98
        row_frame = customtkinter.CTkFrame(
            master=messages_container, fg_color="transparent", corner_radius=0
        )
        row_frame.grid(row=message_row, column=0, sticky="ew", padx=15, pady=8)

        if sender == "user":
            row_frame.grid_columnconfigure(0, weight=1)
            bubble_column = 1
            bubble_sticky = "e"
        else:
            row_frame.grid_columnconfigure(1, weight=1)
            bubble_column = 0
            bubble_sticky = "w"

        message_frame = customtkinter.CTkFrame(
            master=row_frame, corner_radius=12, fg_color=bubble_color
        )
        message_frame.grid(row=0, column=bubble_column, sticky=bubble_sticky)
        message_frame.grid_columnconfigure(0, weight=1)

        available_width = conversation_canvas.winfo_width()
        maximum_width = (
            max(120, min(680, available_width - 70))
            if available_width > 1
            else 680
        )
        for segment_row, (segment, code_block) in enumerate(
            split_markdown_code_blocks(text)
        ):
            width = message_width(segment, maximum_width)
            textbox = create_read_only_textbox(
                message_frame,
                segment,
                width=width,
                height=message_height(segment, width, code_block),
                fg_color=ELEVATED_SURFACE if code_block else bubble_color,
                text_color=message_text_color,
                font=("Consolas", 12) if code_block else ("Segoe UI", 13),
                border_width=0,
                border_spacing=8,
                corner_radius=0,
                scrollbar_button_color=BORDER,
                scrollbar_button_hover_color=SECONDARY,
                wrap="none" if code_block else "word",
            )
            textbox.grid(
                row=segment_row, column=0, sticky="ew", pady=(0, 4)
            )
            message_text_widgets.append((textbox, segment, code_block))

        if follow_scroll:
            scroll_to_bottom()

        message_row += 1

    Misc.bind(
        conversation_canvas,
        "<Configure>",
        update_message_dimensions,
        add="+",
    )

    def clear_chat_display():
        nonlocal message_row

        for widget in messages_container.winfo_children():
            widget.destroy()

        message_text_widgets.clear()
        message_row = 0

    def show_selected_conversation():
        nonlocal message_row
        clear_chat_display()

        selected_conversation = conversation_data.get_selected_conversation()

        if selected_conversation is None:
            title_label.configure(text = "Optimizer")
            return

        title_label.configure(text = selected_conversation["title"])

        messages = conversation_data.get_selected_messages()

        if messages is None:
            return

        if not messages:
            welcome_label = customtkinter.CTkLabel(
                messages_container,
                text="How can Optimizer help?",
                text_color=TEXT,
                font=("Segoe UI", 25, "bold"),
            )
            welcome_label.grid(row=0, column=0, pady=(110, 8))
            message_row = 1
            return

        for message in messages:
            display_message(message["content"], message["role"])

        scroll_to_bottom()

    def save_or_warn():
        success = conversation_data.save_data()

        if success:
            return True

        messagebox.showwarning(
            "Save Warning",
            "The change is currently in memory, "
            "but couldn't be saved to disk. "
            "It may be lost after restarting."
        )

        return False

    def open_folder_settings(folder_id):
        nonlocal settings_window

        folder_context = conversation_data.get_folder_context(folder_id)

        if folder_context is None:
            messagebox.showerror("Folder Error",
                                 "Folder not found.")
            return

        if settings_window is not None and settings_window.winfo_exists():
            settings_window.lift()
            settings_window.focus()
            return

        settings_window = customtkinter.CTkToplevel(master = parent)
        settings_window.title(
            f"Folder Settings - {folder_context['name']}"
        )
        settings_window.geometry("570x630")
        settings_window.minsize(400, 500)
        settings_window.grid_columnconfigure(0, weight = 1)
        settings_window.grid_rowconfigure(5, weight = 1)

        instruction_label = customtkinter.CTkLabel(
            master = settings_window, text = "Shared Instructions",
            text_color = TEXT
        )
        instruction_label.grid(row = 1, column = 0, sticky = 'w', padx = 20)

        instruction_box = customtkinter.CTkTextbox(
            master = settings_window, height = 150,
            fg_color = SURFACE, text_color = TEXT,
            border_color = "#3A424E", border_width = 1,
            corner_radius = 8
        )
        instruction_box.grid(row = 2, column = 0, sticky = 'ew', padx = 20, pady = 10)
        instruction_box.insert("1.0", folder_context["instructions"])

        save_instructions_button = customtkinter.CTkButton(
            master = settings_window, text = "Save Instructions",
            fg_color = SECONDARY, hover_color = PRIMARY,
            text_color = "#FFFFFF"
        )
        save_instructions_button.grid(row = 3, column = 0, sticky = 'e', padx = 20, pady = 5)

        knowledge_label = customtkinter.CTkLabel(
            master = settings_window, text = "Shared Knowledge",
            text_color = TEXT
        )
        knowledge_label.grid(row = 4, column = 0, sticky = "w", padx = 20, pady = (15, 5))

        knowledge_scroll_frame = customtkinter.CTkScrollableFrame(
            master = settings_window, fg_color = BACKGROUND,
            corner_radius = 8
        )
        knowledge_scroll_frame.grid(row = 5, column = 0, sticky = 'nsew', padx = 20, pady = 5)
        knowledge_scroll_frame.grid_columnconfigure(0, weight = 1)

        knowledge_container = customtkinter.CTkFrame(
            master = knowledge_scroll_frame, fg_color = "transparent"
        )
        knowledge_container.grid(row = 0, column = 0, sticky = 'ew')
        knowledge_container.grid_columnconfigure(0, weight = 1)

        add_note_frame = customtkinter.CTkFrame(
            master = settings_window, fg_color = "transparent"
        )
        add_note_frame.grid(row = 6, column = 0, sticky = "ew", padx = 20, pady = 10)
        add_note_frame.grid_columnconfigure(0, weight = 1)

        note_entry = customtkinter.CTkEntry(
            master = add_note_frame, placeholder_text = "Add knowledge note...",
            fg_color = SURFACE, border_color = BORDER, text_color = TEXT
        )
        note_entry.grid(row = 0, column = 0, sticky = "ew", padx = (0, 8))

        add_note_button = customtkinter.CTkButton(
            master = add_note_frame, text = "+",
            width = 40, height = 35, fg_color = SECONDARY,
            hover_color = PRIMARY, text_color = BACKGROUND
        )
        add_note_button.grid(row = 0, column = 1)

        close_button = customtkinter.CTkButton(master = settings_window, text = "Close",
                                               fg_color = ELEVATED_SURFACE, hover_color = BORDER,
                                               text_color = TEXT)
        close_button.grid(row = 7, column = 0, sticky = 'e', padx = 20, pady = 10)

        def on_save_instructions():
            instructions = instruction_box.get("1.0", "end-1c")

            success = conversation_data.update_folder_instructions(
                folder_id,
                instructions
            )
            if success is False:
                messagebox.showerror("Update failure",
                                     "The instructions could not be uploaded.")
                return

            saved = save_or_warn()

            if saved is True:
                messagebox.showinfo("Saved Successfully",
                                    "Instructions saved.")

        def on_add_knowledge():
            note = note_entry.get()

            note = note.strip()

            if not note:
                messagebox.showwarning("Knowledge Note",
                                       "Knowledge note was not found")
                return

            success = conversation_data.add_folder_knowledge(folder_id, note)
            if success is False:
                messagebox.showwarning("Add Knowledge",
                                       "Could not add note."
                                       "It may already exist.")
                return

            note_entry.delete(0, "end")

            refresh_knowledge()
            save_or_warn()

        def on_remove_knowledge(index):
            current_context = conversation_data.get_folder_context(folder_id)

            if current_context is None:
                return

            notes = current_context["knowledge"]

            if not isinstance(index, int) or isinstance(index, bool):
                return

            if index < 0 or index >= len(notes):
                return

            confirmed = messagebox.askyesno(
                "Remove Knowledge",
                f"Are you sure you want to remove this note?\n\n{notes[index]}",
                parent = settings_window
            )
            if not confirmed:
                return

            success = conversation_data.remove_folder_knowledge(folder_id, index)
            if not success:
                messagebox.showerror("Removal Error",
                                     "Could not remove the knowledge note.",
                                     parent = settings_window)
                return

            refresh_knowledge()
            save_or_warn()

        def refresh_knowledge():
            for widget in knowledge_container.winfo_children():
                widget.destroy()

            current_context = conversation_data.get_folder_context(folder_id)

            if current_context is None:
                return

            notes = current_context["knowledge"]

            if not notes:
                not_note_label = customtkinter.CTkLabel(master = knowledge_container,
                                                    text = "No knowledge notes yet.",
                                                    text_color = SECONDARY_TEXT)
                not_note_label.grid(row = 0, column = 0)

                return

            for index, note in enumerate(notes):
                note_frame = customtkinter.CTkFrame(master = knowledge_container,
                                                    fg_color = ELEVATED_SURFACE, corner_radius = 8)
                note_frame.grid(row = index, column = 0, sticky = 'ew', pady = 4)
                note_frame.grid_columnconfigure(0, weight = 1)

                note_textbox = create_read_only_textbox(
                    note_frame,
                    note,
                    width=350,
                    height=min(180, max(52, (note.count("\n") + 1) * 22 + 16)),
                    fg_color=ELEVATED_SURFACE,
                    text_color=TEXT,
                    font=("Segoe UI", 12),
                    border_width=0,
                    border_spacing=6,
                    corner_radius=0,
                    scrollbar_button_color=BORDER,
                    scrollbar_button_hover_color=SECONDARY,
                )
                note_textbox.grid(row=0, column=0, sticky="ew", padx=8, pady=4)

                delete_button = customtkinter.CTkButton(master = note_frame, text = "✕",
                                                        width = 32, height = 32, fg_color = ELEVATED_SURFACE,
                                                        hover_color = "#7F1D1D", text_color = TEXT,
                                                        command = lambda idx = index: on_remove_knowledge(idx))
                delete_button.grid(row = 0, column = 1, padx = 6)

        def close_settings():
            nonlocal settings_window

            if settings_window is not None and settings_window.winfo_exists():
                settings_window.destroy()

            settings_window = None

        save_instructions_button.configure(command=on_save_instructions)

        add_note_button.configure(command=on_add_knowledge)

        close_button.configure(command=close_settings)

        settings_window.protocol("WM_DELETE_WINDOW", close_settings)

        refresh_knowledge()
        
    def refresh_sidebar():
        for widget in folders_container.winfo_children():
            widget.destroy()

        folders = conversation_data.get_all_folders()

        folder_row = 0

        for folder in folders:
            folder_id = folder["id"]
            folder_name = folder["name"]

            folder_frame = customtkinter.CTkFrame(master = folders_container, fg_color = "transparent")
            folder_frame.grid(row = folder_row, column = 0, sticky = 'ew', pady = 4)
            folder_frame.grid_columnconfigure(0, weight = 1)

            if folder_id == selected_folder_id:
                folder_color = ELEVATED_SURFACE

            else:
                folder_color = SIDEBAR

            if folder_id in expanded_folder_ids:
                folder_arrow = "▾"

            else:
                folder_arrow = "▸"

            folder_button = customtkinter.CTkButton(master = folder_frame, text = folder_arrow + " " + folder_name,
                                                    fg_color = folder_color, hover_color = "#353535",
                                                    text_color = TEXT, anchor = "w", corner_radius = 8,
                                                    height = 34, command = lambda fid = folder_id: on_folder_clicked(fid))
            folder_button.grid(row = 0, column = 0, sticky = 'ew')

            settings_button = customtkinter.CTkButton(master = folder_frame, text = "⚙", width = 34, height = 34,
                                                      fg_color = "transparent", hover_color = "#353535",
                                                      text_color = SECONDARY_TEXT, corner_radius = 8, command = lambda fid = folder_id: open_folder_settings(fid))
            settings_button.grid(row = 0, column = 1, sticky = 'e', padx = (4, 0))

            if folder_id in expanded_folder_ids:
                conversation_row = 1

                for conversation in folder["conversations"]:
                    conversation_id = conversation["id"]

                    active_folder_id = conversation_data.ACTIVE_SELECTION["folder_id"]
                    active_conversation_id = conversation_data.ACTIVE_SELECTION["conversation_id"]

                    if active_folder_id == folder_id and active_conversation_id == conversation_id:
                        conversation_color = ELEVATED_SURFACE
                        conversation_text_color = "#FFFFFF"
                    else:
                        conversation_color = "transparent"
                        conversation_text_color = SECONDARY_TEXT

                    conversation_button = customtkinter.CTkButton(master = folder_frame, text = conversation["title"],
                                                                  fg_color = conversation_color, hover_color = "#353535",
                                                                  text_color = conversation_text_color, anchor = "w",
                                                                  height = 30, corner_radius = 8,
                                                                  command = lambda fid = folder_id, cid = conversation_id: on_conversation_clicked(fid, cid))
                    conversation_button.grid(row = conversation_row, column = 0, columnspan = 2, sticky = 'ew', padx = (24, 4), pady = 2)

                    conversation_row += 1
            folder_row += 1
                   
    def on_folder_clicked(folder_id):
        nonlocal selected_folder_id

        folder = conversation_data.get_folder(folder_id)

        if folder is None:
            return

        selected_folder_id = folder_id

        if folder_id in expanded_folder_ids:
            expanded_folder_ids.remove(folder_id)

        else:
            expanded_folder_ids.add(folder_id)

        refresh_sidebar()

    def on_conversation_clicked(folder_id, conversation_id):
        nonlocal selected_folder_id

        success = conversation_data.select_conversation(folder_id, conversation_id)

        if success is False:
            messagebox.showerror("Optimizer", "Conversation not found.")
            return

        selected_folder_id = folder_id
        expanded_folder_ids.add(folder_id)

        show_selected_conversation()

        refresh_sidebar()

    def on_new_folder():
        nonlocal selected_folder_id

        dialog = customtkinter.CTkInputDialog(title = "New Folder", text = "Enter folder name: ")
        folder_name = dialog.get_input()

        if folder_name is None:
            return

        folder_name = folder_name.strip()

        if not folder_name:
            messagebox.showwarning(
                "Bad Entry",
                "Folder name cannot be empty."
            )
            return

        folder_id = f"folder_{uuid4().hex}"

        success = conversation_data.create_folder(folder_id, folder_name)

        if success is False:
            messagebox.showerror("Folder creation error",
                                 "Could not create folder.")
            return

        save_or_warn()

        selected_folder_id = folder_id
        expanded_folder_ids.add(folder_id)

        refresh_sidebar()

    def on_new_chat():
        target_folder = conversation_data.get_folder(selected_folder_id)

        if target_folder is None:
            messagebox.showerror("Invalid folder",
                                 "Choose a valid folder first.")
            return

        dialog = customtkinter.CTkInputDialog(title = "New Conversation",
                                              text = "Enter conversation title: ")
        conversation_title = dialog.get_input()

        if conversation_title is None:
            return

        conversation_title = conversation_title.strip()

        if not conversation_title:
            conversation_title = "New Chat"

        conversation_id = f"chat_{uuid4().hex}"

        success = conversation_data.create_conversation(
            selected_folder_id, conversation_id, conversation_title
        )

        if success == False:
            messagebox.showerror("Conversation creation error",
                                 "Could not create conversation.")
            return

        selection_succeeds = conversation_data.select_conversation(
            selected_folder_id,
            conversation_id
        )

        if not selection_succeeds:
            messagebox.showerror(
                "Selection Error",
                "Could not select the new conversation."
            )
            return

        save_or_warn()

        expanded_folder_ids.add(selected_folder_id)

        show_selected_conversation()
        refresh_sidebar()

    def on_chat_destroyed(event):
        if event.widget is main_frame:
            request_lifecycle.close()
            backend.close()

    # CTkFrame.bind targets its canvas. Observe destruction of the frame itself.
    Misc.bind(
        main_frame, "<Destroy>",
        on_chat_destroyed,
        add = "+"
    )

    def check_ai_results():

        try:
            while True:
                result = result_queue.get_nowait()

                if not request_lifecycle.matches(result["request_id"]):
                    continue

                try:
                    folder_id = result["folder_id"]
                    conversation_id = result["conversation_id"]

                    if result["status"] == "success":
                        response = result["response"]

                        if not isinstance(response, str) or not response.strip():
                            messagebox.showerror(
                                "Optimizer",
                                "The model returned an empty response."
                            )
                        else:
                            saved = conversation_data.add_message(
                                folder_id,
                                conversation_id,
                                "optimizer",
                                response
                            )

                            if saved:
                                save_or_warn()

                                current_folder = conversation_data.ACTIVE_SELECTION["folder_id"]
                                current_chat = conversation_data.ACTIVE_SELECTION["conversation_id"]

                                if (
                                    current_folder == folder_id
                                    and current_chat == conversation_id
                                ):
                                    display_message(response, "optimizer")
                                    backend.read_reply(response)
                            else:
                                messagebox.showerror(
                                    "Optimizer",
                                    "Could not save the AI response."
                                )
                    else:
                        messagebox.showerror(
                            "Optimizer",
                            result["response"]
                        )

                except Exception as error:
                    print(f"AI result handling error: {error}")
      
                finally:
                    request_lifecycle.finish(result["request_id"])

                    if request_lifecycle.state != REQUEST_CLOSED:
                        generating_status.configure(text = "")
                        send_button.configure(image=send_icon, state="normal")

        except queue.Empty:
            pass

        except Exception as error:
            print(f"AI result polling error: {error}")

        finally:
            if request_lifecycle.state != REQUEST_CLOSED:
                try:
                    if main_frame.winfo_exists():
                        main_frame.after(100, check_ai_results)

                except Exception as error:
                    print(f"Could not reschedule AI polling: {error}")
                    request_lifecycle.close()

    def send_message():

        if request_lifecycle.state == REQUEST_CLOSED:
            return

        if request_lifecycle.state == REQUEST_GENERATING:
            return
        
        active_conversation = conversation_data.get_selected_conversation()

        if active_conversation is None:
            messagebox.showinfo("Conversation creation error",
                                "Create or select a conversation first.")
            return

        user_message = message_entry.get().strip()

        if not user_message:
            return

        folder_id = conversation_data.ACTIVE_SELECTION["folder_id"]
        conversation_id = conversation_data.ACTIVE_SELECTION["conversation_id"]

        if conversation_data.get_conversation(folder_id, conversation_id) is None:
            messagebox.showerror("Optimizer", "The selected conversation could not be found.")
            return

        success = conversation_data.add_message(
            folder_id,
            conversation_id,
            "user",
            user_message
        )

        if not success:
            messagebox.showerror("Message error",
                                 "Your message could not be added. Try again.")
            return

        display_message(user_message, "user", force_scroll=True)

        message_entry.delete(0, "end")

        save_or_warn()

        try:
            model_messages = context_engine.build_model_messages(
                folder_id,
                conversation_id
            )

            if not isinstance(model_messages, list) or not model_messages:
                raise ValueError("Could not construct conversation context.")

            last_message = model_messages[-1]

            if not isinstance(last_message, dict):
                raise ValueError("Invalid final context message.")

            if last_message.get("role") != "user":
                raise ValueError("Context does not end with a user message.")

        except Exception as error:
            print(f"Context snapshot error: {error}")

            messagebox.showerror(
                "Optimizer",
                "Could not prepare the AI request."
            )
            return

        request_id = uuid4().hex

        try:
            request_lifecycle.start(
                request_id,
                folder_id,
                conversation_id
            )

        except RequestLifecycleError as error:
            print(f"Request lifecycle error: {error}")

            messagebox.showerror("Optimizer",
                                 "Could not start the AI request.")

            return

        provider = backend.settings["active_provider"]
        model = backend.settings["selected_models"].get(provider)
        generating_status.configure(text=f"Generating with {provider}…")

        send_button.configure(image=send_icon, state="disabled")

        thread = threading.Thread(
            target = run_ai_worker,
            args = (
                request_id,
                folder_id,
                conversation_id,
                provider,
                model_messages,
                result_queue
            ),
            kwargs={"model": model},
            daemon = True
        )

        try:
            thread.start()
        except RuntimeError as error:
            print(f"Could not start AI worker: {error}")

            request_lifecycle.finish(request_id)

            generating_status.configure(text = "")
            send_button.configure(image=send_icon, state="normal")

            messagebox.showerror("Optimizer",
                                 "Could not start the AI request.")

    new_folder_button.configure(command=on_new_folder)

    new_chat_button.configure(command=on_new_chat)

    send_button.configure(command=send_message)

    refresh_sidebar()
    show_selected_conversation()

    main_frame.after(100, check_ai_results)
    return backend