import dearpygui.dearpygui as dpg


def get_inputs_on_generate() -> dict:
    values = {key: dpg.get_value(tag) for key, tag in ON_GENERATE_INPUT_TAGS.items()}

    values["throat_sizing_method"] = ("mass_flow" if dpg.get_value("check_mass_flow_rate") else "given_radius" if dpg.get_value("check_Rt") else None)
    values["nozzle_type"] = ("conical" if dpg.get_value("check_conical") else "bell" if dpg.get_value("check_bell") else None)

    return values

def get_inputs_on_solve() -> dict:
    values = {key: dpg.get_value(tag) for key, tag in ON_SOLVE_INPUT_TAGS.items()}

    return values


# Key -> Value dicts
ON_GENERATE_INPUT_TAGS = {
    "oxidizer"                 : "input_oxidizer",
    "fuel"                     : "input_fuel",
    "Pc"                       : "input_Pc",
    "unit_Pc"                  : "unit_Pc",
    "MR"                       : "input_MR",
    "mass_flow_rate"           : "input_mass_flow_rate",
    "unit_mass_flow_rate"      : "unit_mass_flow_rate",
    "Rt"                       : "input_Rt",
    "unit_Rt"                  : "unit_Rt",
    "eps"                      : "input_eps",
    "CR"                       : "input_CR",
    "L_star"                   : "input_L_star",
    "unit_L_star"              : "unit_L_star",
    "nozzle_length_percentage" : "input_nozzle_length_percentage",
    "nozzle_angle"             : "input_nozzle_angle",
    "nozzle_resolution"        : "input_nozzle_resolution",
}

ON_SOLVE_INPUT_TAGS = {
    "coolant"                          : "input_coolant",
    "coolant_mass_flow_rate"           : "input_coolant_mass_flow",
    "unit_coolant_mass_flow_rate"      : "unit_mass_flow_rate",
    "coolant_inlet_temperature"        : "input_coolant_inlet_temperature",
    "unit_coolant_inlet_temperature"   : "unit_coolant_inlet_temperature",
    "coolant_inlet_pressure"           : "input_coolant_inlet_pressure",
    "unit_coolant_inlet_pressure"      : "unit_coolant_inlet_pressure",
    "wall_material"                    : "input_wall_material",
    "wall_thickness"                   : "input_wall_thickness",
    "unit_wall_thickness"              : "unit_wall_thickness",
    "N_cooling_channels"               : "input_N_cooling_channels",
    "jacket_resolution"                : "input_jacket_resolution",
    "channel_roughness"                : "input_channel_roughness",
    "interpolation_type"               : "interpolation_type",
    "pressure_drop_model"              : "input_pressure_drop_model",
    "cold_side_model"                  : "input_cold_side_model",
    "hot_side_model"                   : "input_hot_side_model",
    "wall_model"                       : "input_wall_model",
    "N_injectors"                      : "input_N_injectors",
    "injector_velocity_ratio"          : "input_injector_velocity_ratio",
}