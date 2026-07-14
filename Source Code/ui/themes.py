import dearpygui.dearpygui as dpg
from pathlib import Path
import sys


# Base path getter
def get_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        # Running from source (python main.py).
        return Path(__file__).resolve().parent.parent

class Font:
    def __init__(self):
        self.default_font = None

    FONT_PATH = get_base_path() / "assets" / "Inter.ttf"

    def build_font(self):
        with dpg.font_registry():
            self.default_font = dpg.add_font(str(self.FONT_PATH), 16)

FONT = Font()
ICON = get_base_path() / "assets" / "icon.ico"


def build_themes():
        with dpg.theme(tag="disabled_float_entry_theme"):
            with dpg.theme_component(dpg.mvInputFloat, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (110, 110, 110, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (10, 10, 10, 255))

        with dpg.theme(tag="disabled_combo_theme"):
            with dpg.theme_component(dpg.mvCombo, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (110, 110, 110, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (10, 10, 10, 255))

        with dpg.theme(tag="disabled_int_entry_theme"):
            with dpg.theme_component(dpg.mvInputInt, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (110, 110, 110, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (10, 10, 10, 255))

        with dpg.theme(tag="button_theme"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button,        (30,  60,  110, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (40,  70,  125, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,  (20,  50,  95,  255))



# Setter functions for enabled/disabled entries
def set_enabled(tag):
    dpg.configure_item(tag, enabled=True)
    dpg.bind_item_theme(tag, 0)  

def set_disabled(tag):
    dpg.configure_item(tag, enabled=False)
    if "Combo" in dpg.get_item_type(tag):
        dpg.bind_item_theme(tag, "disabled_combo_theme")
    elif "Int" in dpg.get_item_type(tag):
        dpg.bind_item_theme(tag, "disabled_int_entry_theme")
    else:
        dpg.bind_item_theme(tag, "disabled_float_entry_theme")