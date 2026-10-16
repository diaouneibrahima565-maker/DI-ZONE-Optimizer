import customtkinter
import threading
import queue

import optimizer_core
import conversation_data

from PIL import Image
from pathlib import Path
from uuid import uuid4
from tkinter import messagebox


def show_chat_interface(parent):
    main_frame = customtkinter.CTkFrame(master = parent, fg_color = "#171717")
    main_frame.grid(row = 0, column = 0, sticky = 'nsew')
    main_frame.grid_columnconfigure(0, weight = 0)
    main_frame.grid_columnconfigure(1, weight = 1)
    main_frame.grid_rowconfigure(0, weight = 1)


    sidebar_frame = customtkinter.CTkFrame(master = main_frame, width = 260, corner_radius = 0, fg_color = "#171717")
    sidebar_frame.grid(row = 0, column = 0, sticky = 'ns')
    sidebar_frame.grid_propagate(False)
    sidebar_frame.grid_columnconfigure(0, weight = 1)
    sidebar_frame.grid_rowconfigure(2, weight = 1)

    chat_panel = customtkinter.CTkFrame(master = main_frame, fg_color = "#212121", corner_radius = 0)
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

    title_text = (
        " Optimizer"
        if optimizer_icon is not None
        else "🧠  Optimizer"
    )

    sidebar_title = customtkinter.CTkLabel(master = sidebar_frame,
                                           text = title_text, image = optimizer_icon,
                                           compound = "left", text_color = "#F8FAFC",
                                           font = ("Segoe UI", 20, "bold"), fg_color = "transparent")
    sidebar_title.grid(row = 0, column = 0, sticky = "w", padx = 20, pady = 20)

    sidebar_actions = customtkinter.CTkFrame(master = sidebar_frame, fg_color = "transparent")
    sidebar_actions.grid(row = 1, column = 0, sticky = 'ew', padx = 12, pady = (0, 10))
    sidebar_actions.grid_columnconfigure(0, weight = 1)
    sidebar_actions.grid_columnconfigure(1, weight = 1)

    new_folder_button = customtkinter.CTkButton(master = sidebar_actions, text = "+ Folder",
                                                fg_color = '#303030', hover_color = '#404040',
                                                text_color = "#F8FAFC", height = 36, corner_radius = 8, width = 100)
    new_folder_button.grid(row = 0, column = 0, sticky = 'ew', padx = 4, pady = 4)

    new_chat_button = customtkinter.CTkButton(master = sidebar_actions, text = "+ Chat",
                                              fg_color = "#0E7490", hover_color = '#155E75',
                                              text_color = "#FFFFFF", height = 36, corner_radius = 8, width = 100)
    new_chat_button.grid(row = 0, column = 1, sticky = 'ew', padx = 4, pady = 4)

    folders_scroll_frame = customtkinter.CTkScrollableFrame(master = sidebar_frame, fg_color = '#171717', corner_radius = 0)
    folders_scroll_frame.grid(row = 2, column = 0, sticky = 'nsew', padx = 5)
    folders_scroll_frame.grid_columnconfigure(0, weight = 1)

    folders_container = customtkinter.CTkFrame(master = folders_scroll_frame, fg_color = "transparent")
    folders_container.grid(row = 0, column = 0, sticky = 'ew')
    folders_container.grid_columnconfigure(0, weight = 1)

    title_label = customtkinter.CTkLabel(master = chat_panel, text = "Optimizer", text_color = "#F8FAFC",
                                         font = ("Segoe UI", 20, "bold"))
    title_label.grid(row = 0, column = 0, sticky = 'w', padx = 20, pady = 10)

    conversation_frame = customtkinter.CTkScrollableFrame(master = chat_panel, corner_radius = 12, fg_color = "#212121")
    conversation_frame.grid(row = 1, column = 0, sticky = 'nsew', padx = 20, pady = 10)
    conversation_frame.grid_columnconfigure(0, weight = 1)

    messages_container = customtkinter.CTkFrame(master = conversation_frame, fg_color = "transparent", corner_radius = 0)
    messages_container.grid(row = 0, column = 0, sticky = "ew")
    messages_container.grid_columnconfigure(0, weight = 1)

    input_frame = customtkinter.CTkFrame(master = chat_panel, corner_radius = 15, fg_color = "#2F2F2F")
    input_frame.grid(row = 2, column = 0, sticky = 'ew', padx = 20, pady = 10)
    input_frame.grid_columnconfigure(0, weight = 1)

    message_entry = customtkinter.CTkEntry(master = input_frame, placeholder_text = "Message Optimizer...", fg_color = "#262626",
                                           border_color = '#3A424E', text_color = '#F8FAFC',
                                           placeholder_text_color = '#929BA8', corner_radius = 15)
    message_entry.grid(row = 0, column = 0, sticky = 'ew', padx = (20, 8), pady = 10)

    send_button = customtkinter.CTkButton(master = input_frame, text = "⬆", width = 44,
                                          height = 44, corner_radius = 22, fg_color = '#0E7490',
                                          hover_color = '#155E75', text_color = '#FFFFFF',
                                          font = ("Segoe UI", 20, "bold"))
    send_button.grid(row = 0, column = 1, sticky = 'e', padx = (8, 20), pady = 10)

    generating_status = customtkinter.CTkLabel(
        master = chat_panel, text = "", text_color = "#A3A3A3", font = ("Segoe UI", 12)
    )
    generating_status.grid(row = 3, column = 0, sticky = 'w', padx = 25, pady = (0, 8))

    message_row = 0

    selected_folder_id = conversation_data.ACTIVE_SELECTION["folder_id"]

    expanded_folder_ids = set()

    settings_window = None

    result_queue = queue.Queue()

    request_in_progress = False
    active_request_id = None

    for folder in conversation_data.get_all_folders():
        expanded_folder_ids.add(folder["id"])

    def display_message(text, sender):
        nonlocal message_row

        if sender == "user":
            bubble_color = "#0E7490"
            message_alignment = "e"

        elif sender == "optimizer":
            bubble_color = "#212121"
            message_alignment = "w"

        message_frame = customtkinter.CTkFrame(master = messages_container,
                                               corner_radius = 12,
                                               fg_color = bubble_color)
        message_frame.grid(row = message_row, column = 0, sticky = message_alignment, padx = 15, pady = 8)

        message_label = customtkinter.CTkLabel(master = message_frame, text = text, text_color = "#F8FAFC",
                                               wraplength = 500,
                                               justify = "left")
        message_label.grid(row = 0, column = 0, padx = 15, pady = 10)

        message_row += 1

    def clear_chat_display():
        nonlocal message_row

        for widget in messages_container.winfo_children():
            widget.destroy()

        message_row = 0

    def show_selected_conversation():
        clear_chat_display()

        selected_conversation = conversation_data.get_selected_conversation()

        if selected_conversation is None:
            title_label.configure(text = "Optimizer")
            return

        title_label.configure(text = selected_conversation["title"])

        messages = conversation_data.get_selected_messages()

        if messages is None:
            return

        for message in messages:
            display_message(message["content"], message["role"])

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
            text_color = "#F8FAFC"
        )
        instruction_label.grid(row = 1, column = 0, sticky = 'w', padx = 20)

        instruction_box = customtkinter.CTkTextbox(
            master = settings_window, height = 150,
            fg_color = "#262626", text_color = "#F8FAFC",
            border_color = "#3A424E", border_width = 1,
            corner_radius = 8
        )
        instruction_box.grid(row = 2, column = 0, sticky = 'ew', padx = 20, pady = 10)
        instruction_box.insert("1.0", folder_context["instructions"])

        save_instructions_button = customtkinter.CTkButton(
            master = settings_window, text = "Save Instructions",
            fg_color = "#0E7490", hover_color = "#155E75",
            text_color = "#FFFFFF"
        )
        save_instructions_button.grid(row = 3, column = 0, sticky = 'e', padx = 20, pady = 5)

        knowledge_label = customtkinter.CTkLabel(
            master = settings_window, text = "Shared Knowledge",
            text_color = "#F8FAFC"
        )
        knowledge_label.grid(row = 4, column = 0, sticky = "w", padx = 20, pady = (15, 5))

        knowledge_scroll_frame = customtkinter.CTkScrollableFrame(
            master = settings_window, fg_color = "#212121",
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
            fg_color = "#262626", border_color = "#3A424E", text_color = "#F8FAFC"
        )
        note_entry.grid(row = 0, column = 0, sticky = "ew", padx = (0, 8))

        add_note_button = customtkinter.CTkButton(
            master = add_note_frame, text = "+",
            width = 40, height = 35, fg_color = "#0E7490",
            hover_color = "#155E75", text_color = "#FFFFFF"
        )
        add_note_button.grid(row = 0, column = 1)

        close_button = customtkinter.CTkButton(master = settings_window, text = "Close",
                                               fg_color = "#303030", hover_color = "#404040",
                                               text_color = "#F8FAFC")
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
                                       "Could not add note." \
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
                                                    text_color = "#A3A3A3")
                not_note_label.grid(row = 0, column = 0)

                return

            for index, note in enumerate(notes):
                note_frame = customtkinter.CTkFrame(master = knowledge_container,
                                                    fg_color = "#303030", corner_radius = 8)
                note_frame.grid(row = index, column = 0, sticky = 'ew', pady = 4)
                note_frame.grid_columnconfigure(0, weight = 1)

                note_label = customtkinter.CTkLabel(master = note_frame, text = note,
                                                    text_color = '#F8FAFC', wraplength = 350,
                                                    justify = "left", anchor = "w")
                note_label.grid(row = 0, column = 0, sticky = "ew", padx = 10, pady = 8)

                delete_button = customtkinter.CTkButton(master = note_frame, text = "✕",
                                                        width = 32, height = 32, fg_color = "#303030",
                                                        hover_color = "#7F1D1D", text_color = "#F8FAFC",
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
                folder_color = '#303030'

            else:
                folder_color = "#171717"

            if folder_id in expanded_folder_ids:
                folder_arrow = "▾"

            else:
                folder_arrow = "▸"

            folder_button = customtkinter.CTkButton(master = folder_frame, text = folder_arrow + " " + folder_name,
                                                    fg_color = folder_color, hover_color = "#353535",
                                                    text_color = "#F8FAFC", anchor = "w", corner_radius = 8,
                                                    height = 34, command = lambda fid = folder_id: on_folder_clicked(fid))
            folder_button.grid(row = 0, column = 0, sticky = 'ew')

            settings_button = customtkinter.CTkButton(master = folder_frame, text = "⚙", width = 34, height = 34,
                                                      fg_color = "transparent", hover_color = "#353535",
                                                      text_color = "#A3A3A3", corner_radius = 8, command = lambda fid = folder_id: open_folder_settings(fid))
            settings_button.grid(row = 0, column = 1, sticky = 'e', padx = (4, 0))

            if folder_id in expanded_folder_ids:
                conversation_row = 1

                for conversation in folder["conversations"]:
                    conversation_id = conversation["id"]

                    active_folder_id = conversation_data.ACTIVE_SELECTION["folder_id"]
                    active_conversation_id = conversation_data.ACTIVE_SELECTION["conversation_id"]

                    if active_folder_id == folder_id and active_conversation_id == conversation_id:
                        conversation_color = "#303030"
                        conversation_text_color = "#FFFFFF"
                    else:
                        conversation_color = "transparent"
                        conversation_text_color = "#A3A3A3"

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
                "Bad Entry"
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

        if target_folder == None:
            messagebox.showerror("Invalid folder",
                                 "Choose a valid folder first.")
            return

        dialog = customtkinter.CTkInputDialog(title = "New Conversation",
                                              text = "Enter conversation title: ")
        conversation_title = dialog.get_input()

        if conversation_title == None:
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

    def ai_worker(
            request_id, folder_id, conversation_id, provider_name
    ):
        try:
            response = optimizer_core.generate_conversation_reply(
                folder_id, conversation_id, provider_name = provider_name
            )

            result_queue.put({
                "request_id": request_id,
                "folder_id": folder_id,
                "conversation_id": conversation_id,
                "status": "success",
                "response": response
            })

        except Exception as error:
            print(f"AI generation error: {error}")

            result_queue.put({
            "request_id": request_id,
            "folder_id": folder_id,
            "conversation_id": conversation_id,
            "status": "error",
            "response": "AI generation failed. Please try again."
            })


    def check_ai_results():
        nonlocal request_in_progress, active_request_id

        try:
            while True:
                result = result_queue.get_nowait()

                if result["request_id"] != active_request_id:
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
                    request_in_progress = False
                    active_request_id = None

                    generating_status.configure(text="")
                    send_button.configure(state="normal")

        except queue.Empty:
            pass

        if main_frame.winfo_exists():
            main_frame.after(100, check_ai_results)
            
    def send_message():
        nonlocal request_in_progress, active_request_id
        print(
            "SEND DEBUG:",
            "busy =", request_in_progress,
            "button =", send_button.cget("state")
        )

        if request_in_progress:
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

        display_message(user_message, "user")

        message_entry.delete(0, "end")

        save_or_warn()

        request_id = uuid4().hex

        request_in_progress = True
        active_request_id = request_id

        generating_status.configure(text = "Generating response with Qwen3 1.7B...")

        send_button.configure(state = "disabled")

        thread = threading.Thread(
            target = ai_worker,
            args = (
                request_id,
                folder_id,
                conversation_id,
                "ollama"
            ),
            daemon = True
        )

        try:
            thread.start()
        except RuntimeError as error:
            print(f"Could not start AI worker: {error}")

            request_in_progress = False
            active_request_id = None

            generating_status.configure(text = "")
            send_button.configure(state = "normal")

            messagebox.showerror("Optimizer", "Could not start the AI request.")

    new_folder_button.configure(command=on_new_folder)

    new_chat_button.configure(command=on_new_chat)

    send_button.configure(command=send_message)

    refresh_sidebar()
    show_selected_conversation()

    main_frame.after(100, check_ai_results)