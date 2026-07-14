import dearpygui.dearpygui as dpg
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

def show_errors(errors):
    if dpg.does_item_exist("error_popup"):
        dpg.delete_item("error_popup")

    for error in errors:
        print(error)

    with dpg.window(tag="error_popup", label="Input Errors", modal=True, no_resize=True, width=400):
        for e in errors:
            dpg.add_text(f"• {e}", color=(255, 80, 80), wrap=370)
        dpg.add_spacer(height=8)
        dpg.add_button(label="OK", width=-1, callback=lambda: dpg.delete_item("error_popup"))


def ask_save_path(default_filename: str) -> Path | None:
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    root.update()

    path = filedialog.asksaveasfilename(
        parent=root,
        defaultextension=".txt",
        initialfile=default_filename,
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="Save Output As",
    )

    root.destroy()
    return Path(path) if path else None