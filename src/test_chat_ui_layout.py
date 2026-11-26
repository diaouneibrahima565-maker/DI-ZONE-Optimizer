import tkinter as tk
import time
import unittest
from unittest.mock import patch

import customtkinter as ctk

import chat_ui
import conversation_data
import settings_data


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class TestChatTextLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = ctk.CTk()
        except tk.TclError as error:
            raise unittest.SkipTest(f"Graphical display unavailable: {error}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_long_response_wraps_and_tracks_window_width(self):
        code_block = "```python\n" + ("print('response')\n" + ("x" * 800)) + "\n```"
        content = "A paragraph starts here.\n\n" + ("X" * 1000) + "\n\n" + code_block
        folder_id = "layout-test-folder"
        conversation_id = "layout-test-conversation"
        folder = {
            "id": folder_id,
            "name": "Layout test",
            "conversations": [{"id": conversation_id, "title": "Long response"}],
        }
        selection = {
            "folder_id": folder_id,
            "conversation_id": conversation_id,
        }

        ctk.set_widget_scaling(1.0)
        self.root.geometry("900x650")
        self.root.deiconify()
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        parent = ctk.CTkFrame(self.root)
        parent.grid(row=0, column=0, sticky="nsew")
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        try:
            with (
                patch.object(conversation_data, "ACTIVE_SELECTION", selection),
                patch.object(conversation_data, "get_all_folders", return_value=[folder]),
                patch.object(
                    conversation_data,
                    "get_selected_conversation",
                    return_value={"id": conversation_id, "title": "Long response"},
                ),
                patch.object(
                    conversation_data,
                    "get_selected_messages",
                    return_value=[{"content": content, "role": "optimizer"}],
                ),
                patch.object(
                    settings_data,
                    "load_settings",
                    return_value=settings_data.DEFAULT_SETTINGS,
                ),
            ):
                chat_ui.show_chat_interface(parent)
                self.root.update()

                textboxes = [
                    widget for widget in descendants(parent)
                    if isinstance(widget, ctk.CTkTextbox)
                ]
                self.assertEqual(
                    "".join(widget.get("1.0", "end-1c") for widget in textboxes),
                    content,
                )
                textbox = next(
                    widget for widget in textboxes
                    if widget._textbox.cget("wrap") == "word"
                )
                code_textbox = next(
                    widget for widget in textboxes
                    if widget._textbox.cget("wrap") == "none"
                )
                conversation_scroll_frame = next(
                    widget for widget in descendants(parent)
                    if isinstance(widget, ctk.CTkScrollableFrame)
                    and any(
                        isinstance(child, ctk.CTkTextbox)
                        for child in descendants(widget)
                    )
                )
                conversation_canvas = conversation_scroll_frame._parent_canvas
                self.assertGreater(
                    textbox._textbox.count("1.0", "end-1c", "displaylines")[0],
                    2,
                )
                self.assertTrue(code_textbox._x_scrollbar.winfo_ismapped())

                narrow_width = max(widget.winfo_width() for widget in textboxes)
                narrow_canvas_width = conversation_canvas.winfo_width()
                self.root.geometry("1300x700")
                deadline = time.monotonic() + 2
                while (
                    time.monotonic() < deadline
                    and conversation_canvas.winfo_width() <= narrow_canvas_width
                ):
                    self.root.update()
                    time.sleep(0.01)
                self.root.update()
                self.assertGreater(conversation_canvas.winfo_width(), narrow_canvas_width)
                self.assertGreater(
                    max(widget.winfo_width() for widget in textboxes),
                    narrow_width,
                )

                ctk.set_widget_scaling(1.25)
                self.root.update()
                self.assertEqual(
                    "".join(widget.get("1.0", "end-1c") for widget in textboxes),
                    content,
                )
        finally:
            parent.destroy()
            self.root.withdraw()
            ctk.set_widget_scaling(1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
