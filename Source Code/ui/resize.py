import dearpygui.dearpygui as dpg

import ui.dynamic as dynamic

# Resize nozzle type inputs
def resize_nozzle_type_inputs():
    if not dpg.does_item_exist("input_nozzle_angle"):
        return
    
    cell_width = dpg.get_item_width("main_window") / 4
    input_w = cell_width * 0.32

    dpg.configure_item("input_nozzle_angle", width=input_w)
    dpg.configure_item("input_nozzle_length_percentage", width=input_w)

# Resize the throat-sizing inputs
def resize_throat_sizing_inputs():
    if not dpg.does_item_exist("input_mass_flow_rate"):
        return
    
    cell_width = dpg.get_item_width("main_window") / 4

    input_w = cell_width * 0.32
    unit_w = cell_width * 0.19

    dpg.configure_item("input_mass_flow_rate", width=input_w)
    dpg.configure_item("input_Rt", width=input_w)

    dpg.configure_item("unit_mass_flow_rate", width=unit_w)
    dpg.configure_item("unit_Rt", width=unit_w)

# Resize the wall material inputs 
def resize_wall_material_inputs():
    if not dpg.does_item_exist("input_wall_material"):
        return

    cell_width = dpg.get_item_width("main_window") / 4

    wall_material_combo_w  = cell_width * 0.35
    wall_thickness_input_w = cell_width * 0.3
    wall_thickness_unit_w  = cell_width * 0.2

    dpg.configure_item("input_wall_material",  width=wall_material_combo_w)
    dpg.configure_item("input_wall_thickness", width=wall_thickness_input_w)
    dpg.configure_item("unit_wall_thickness",  width=wall_thickness_unit_w)



# Live resize of main window
def resize_main_window(sender=None, app_data=None, user_data=None):
    if not dpg.does_item_exist("main_window"):
        return
    
    
    dpg.set_item_pos("main_window", [0, 0])
    dpg.set_item_width("main_window", dpg.get_viewport_client_width())
    dpg.set_item_height("main_window", dpg.get_viewport_client_height())

    resize_nozzle_type_inputs()
    resize_throat_sizing_inputs()
    resize_wall_material_inputs()

    if user_data is not None and user_data["nozzle_parameters"]["x"] is not None:
        dynamic.update_nozzle_canvas(user_data)