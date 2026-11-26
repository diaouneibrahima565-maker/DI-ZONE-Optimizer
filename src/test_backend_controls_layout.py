from contextlib import ExitStack, nullcontext
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

import customtkinter as ctk

import backend_controls
import conversation_data
import knowledge_store
import settings_data


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class TestKnowledgeToolsLayout(unittest.TestCase):
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

    def test_scrolling_wrapping_and_code_horizontal_scroll(self):
        folder_id = "tools-layout-test"
        folder = {"id": folder_id, "name": "Layout test"}
        code = "```python\n" + ("x" * 800) + "\n```"
        plain_text = "unbroken " + ("y" * 800)
        parent = ctk.CTkFrame(self.root)
        entry = ctk.CTkEntry(parent)
        controls = None
        window = None
        created_windows = []
        original_geometry = self.root.geometry()
        self.root.geometry("900x650")
        self.root.deiconify()

        try:
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(
                        conversation_data,
                        "ACTIVE_SELECTION",
                        {"folder_id": folder_id, "conversation_id": "chat"},
                    )
                )
                stack.enter_context(
                    patch.object(conversation_data, "get_folder", return_value=folder)
                )
                stack.enter_context(
                    patch.object(
                        settings_data,
                        "load_settings",
                        return_value=settings_data.DEFAULT_SETTINGS,
                    )
                )
                stack.enter_context(
                    patch.object(
                        knowledge_store,
                        "open_store",
                        return_value=nullcontext(object()),
                    )
                )
                stack.enter_context(
                    patch.object(
                        knowledge_store,
                        "list_memories",
                        side_effect=[
                            [{"id": 1, "content": code}],
                            [{"id": 2, "content": plain_text}],
                        ],
                    )
                )
                original_toplevel = backend_controls.tk.Toplevel

                def create_toplevel(master):
                    created = original_toplevel(master)
                    created_windows.append(created)
                    return created

                stack.enter_context(
                    patch.object(
                        backend_controls.tk,
                        "Toplevel",
                        side_effect=create_toplevel,
                    )
                )

                controls = backend_controls.BackendControls(parent, entry)
                controls.tools_dialog()
                window = created_windows[0]
                window.geometry("520x400")
                self.root.update()

                text_widgets = [
                    widget for widget in descendants(window)
                    if isinstance(widget, tk.Text)
                ]
                steps = next(widget for widget in text_widgets if widget.cget("height") == 5)
                output = next(widget for widget in text_widgets if widget.cget("height") == 10)
                self.assertEqual(steps.cget("wrap"), "word")
                self.assertEqual(output.cget("wrap"), "word")

                list_button = next(
                    widget
                    for widget in descendants(window)
                    if isinstance(widget, ttk.Button)
                    and widget.cget("text") == "List memories"
                )
                list_button.invoke()
                self.root.update()
                self.assertEqual(output.cget("wrap"), "none")
                scrollbars = [
                    widget for widget in descendants(window)
                    if widget.winfo_class() == "TScrollbar"
                ]
                orientations = [str(widget.cget("orient")) for widget in scrollbars]
                self.assertIn("horizontal", orientations)
                horizontal_scrollbar = next(
                    widget for widget in scrollbars
                    if str(widget.cget("orient")) == "horizontal"
                )
                self.assertTrue(horizontal_scrollbar.winfo_ismapped())

                narrow_width = output.winfo_width()
                window.geometry("900x600")
                self.root.update()
                self.assertGreater(output.winfo_width(), narrow_width)

                list_button.invoke()
                self.root.update()
                self.assertEqual(output.cget("wrap"), "word")
                self.assertEqual(
                    output.get("1.0", "end-1c"),
                    f"#2  {plain_text}",
                )
                self.assertGreater(
                    output.count("1.0", "end-1c", "displaylines")[0],
                    1,
                )
        finally:
            if window is not None and window.winfo_exists():
                window.destroy()
            if controls is not None:
                controls.close()
            parent.destroy()
            self.root.withdraw()
            self.root.geometry(original_geometry)
            self.root.update_idletasks()


if __name__ == "__main__":
    unittest.main(verbosity=2)
