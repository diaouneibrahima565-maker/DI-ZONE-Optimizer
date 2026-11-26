import re

import customtkinter


def split_markdown_code_blocks(text):
    parts = re.split(r"(```.*?```)", text, flags=re.DOTALL)
    return [
        (part, part.startswith("```") and part.endswith("```"))
        for part in parts
        if part
    ] or [("", False)]


def create_read_only_textbox(master, text="", **kwargs):
    kwargs.setdefault("wrap", "word")
    kwargs.setdefault("activate_scrollbars", True)

    textbox = customtkinter.CTkTextbox(master=master, **kwargs)
    set_read_only_text(textbox, text)
    return textbox


def set_read_only_text(textbox, text):
    textbox.configure(state="normal")
    try:
        textbox.delete("1.0", "end")
        textbox.insert("1.0", text)
    finally:
        textbox.configure(state="disabled")
