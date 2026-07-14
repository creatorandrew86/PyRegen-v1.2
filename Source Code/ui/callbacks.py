import dearpygui.dearpygui as dpg

from ui.themes import set_enabled, set_disabled
from ui.messages import show_errors
import output.graphs as graphs
import output.files as files



# Nozzle Type Selection Callback
def on_nozzle_type(sender, app_data, user_data):
    if (sender == "check_conical"):
        dpg.set_value("check_conical", True)
        dpg.set_value("check_bell", False)

        set_enabled("input_nozzle_angle")
        set_disabled("input_nozzle_length_percentage")
        

    elif (sender == "check_bell"):
        dpg.set_value("check_conical", False)
        dpg.set_value("check_bell", True)

        set_enabled("input_nozzle_length_percentage")
        set_disabled("input_nozzle_angle")

def on_throat_sizing_method(sender, app_data, user_data):
    if (sender == "check_mass_flow_rate"):
        dpg.set_value("check_mass_flow_rate", True)
        dpg.set_value("check_Rt", False)

        set_enabled("input_mass_flow_rate")
        set_disabled("input_Rt")

        set_enabled("unit_mass_flow_rate")
        set_disabled("unit_Rt")
        
    elif (sender == "check_Rt"):
        dpg.set_value("check_mass_flow_rate", False)
        dpg.set_value("check_Rt", True)

        set_enabled("input_Rt")
        set_disabled("input_mass_flow_rate")

        set_enabled("unit_Rt")
        set_disabled("unit_mass_flow_rate")



# Solver options callbacks
def on_pressure_drop_model_change(sender, app_data):
    model = app_data

    if model in (["Colebrook-Petukhov", "Colebrook"]):
        set_enabled("input_channel_roughness")
    else:
        set_disabled("input_channel_roughness")

def on_hot_side_model_change(sender, app_data):
    model = app_data

    if model == "Bartz Corrected":
        set_enabled("input_N_injectors")
        set_enabled("input_injector_velocity_ratio")
    else:
        set_disabled("input_N_injectors")
        set_disabled("input_injector_velocity_ratio")




# Output callbacks
def on_generate_main_graph(state: dict):
    values = {
        "x_value" : dpg.get_value("combo_graph_x"),
        "y_value" : dpg.get_value("combo_graph_y"),
        "y2_value" : dpg.get_value("combo_graph_y2"),
    }

    main_graph_errors = graphs.main_graph(state, values)
    if main_graph_errors:
        show_errors(main_graph_errors)

def on_write_full_pyregen_output(state: dict):
    files.write_full_pyregen_output(state)