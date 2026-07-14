import dearpygui.dearpygui as dpg
import ctypes

import ui.layout as layout
import ui.themes as themes
import ui.resize as resize


def run_interface(on_generate_nozzle: callable, on_solve: callable, state: dict):
    dpg.create_context()

    # Build the layout
    themes.build_themes()
    themes.FONT.build_font()
    layout.build_interface(on_generate_nozzle, on_solve, state)

    dpg.bind_font(themes.FONT.default_font)

    # Viewport
    dpg.create_viewport(title="PyRegen")
    dpg.set_viewport_small_icon(str(themes.ICON))

    dpg.set_viewport_min_width(width=1250)
    dpg.set_viewport_min_height(height=750)

    dpg.setup_dearpygui()
    dpg.show_viewport()
    size_viewport()
    dpg.set_viewport_resize_callback(resize.resize_main_window, user_data=state)
    resize.resize_main_window(user_data=state)
    dpg.set_primary_window("main_window", False)

    dpg.start_dearpygui()
    dpg.destroy_context()


def size_viewport():
    user32 = ctypes.windll.user32
    screen_width  = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)

    vp_width = 1300
    vp_height = 780

    dpg.set_viewport_width(width=vp_width)
    dpg.set_viewport_height(height=vp_height)

    dpg.set_viewport_pos([(screen_width - vp_width) // 2, (screen_height - vp_height) // 2])
    dpg.set_viewport_pos([200, 80])