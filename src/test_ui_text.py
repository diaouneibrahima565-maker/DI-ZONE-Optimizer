import tkinter as tk
import unittest

import customtkinter as ctk

from ui_text import create_read_only_textbox


class TestReadOnlyTextBox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = ctk.CTk()
        except tk.TclError as error:
            raise unittest.SkipTest(f"Graphical display unavailable: {error}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_wraps_unbroken_content_resizes_and_can_be_copied(self):
        content = "First paragraph.\n\n" + ("x" * 500)
        textbox = create_read_only_textbox(
            self.root,
            content,
            width=220,
            height=90,
            fg_color="#101A14",
            text_color="#B8CEC0",
        )
        textbox.pack(fill="both", expand=True)
        try:
            self.root.deiconify()
            self.root.geometry("260x140")
            self.root.update()

            self.assertEqual(textbox.get("1.0", "end-1c"), content)
            self.assertEqual(textbox._textbox.cget("wrap"), "word")
            self.assertEqual(textbox.cget("state"), "disabled")
            self.assertGreater(
                textbox._textbox.count("1.0", "end-1c", "displaylines")[0],
                2,
            )

            narrow_width = textbox.winfo_width()
            self.root.geometry("480x140")
            self.root.update()
            self.assertGreater(textbox.winfo_width(), narrow_width)

            textbox._textbox.tag_add("sel", "1.0", "end-1c")
            textbox._textbox.event_generate("<<Copy>>")
            self.root.update()
            self.assertEqual(self.root.clipboard_get(), content)
        finally:
            self.root.withdraw()
            textbox.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
