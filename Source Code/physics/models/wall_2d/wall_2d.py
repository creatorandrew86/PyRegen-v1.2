from scipy.sparse.linalg import spsolve
from scipy.interpolate import interp1d
from scipy.sparse import lil_matrix
from scipy.optimize import fsolve
import numpy as np

from core.geometry import generate_mesh
from . import steady_2d_solver as solver

from assets.data import THERMAL_CONDUCTIVITY_DATA


# ── Wall thermal conductivity ─────────────────────────────────────────────────
def _wall_thermal_conductivity(wall_material: str, T_cold_wall: float, station_index: int) -> tuple[float, list[str]]:
    errors = []

    try:
        data = THERMAL_CONDUCTIVITY_DATA[wall_material]
        wall_thermal_conductivity = float(interp1d(data["X"], data["Y"], kind="linear", fill_value="extrapolate")(T_cold_wall))
    except Exception as e:
        errors.append(f"Wall thermal conductivity failed at T={T_cold_wall:.2f} K, station {station_index}: {e}")
        return 0.0, errors
    
    return wall_thermal_conductivity, errors


# ── 2D model ───────────────────────────────────────────────────────────────────
def wall_2d(state: dict, station_index: int, cold_side_model: callable, hot_side_model: callable) -> tuple[float, float, float, list[str]]:
    errors = []

    T_aw      = state["engine_parameters"]["station_T_aw"][station_index]
    R         = state["nozzle_parameters"]["station_R"][station_index]
    coolant_T = state["coolant_parameters"]["station_coolant_T"][-1]

    wall_material  = state["channel_parameters"]["wall_material"]
    wall_thickness = state["channel_parameters"]["wall_thickness"]
    ch             = state["channel_parameters"]["station_ch"][station_index]
    cw             = state["channel_parameters"]["station_cw"][station_index]
    landwidth      = state["channel_parameters"]["station_landwidth"][station_index]
    N_channels     = state["channel_parameters"]["N_cooling_channels"]

    mesh = generate_mesh(nx=100, ny=100, cw=cw, ch=ch, lw=landwidth, t=wall_thickness)

    A_cold = (2.0  * ch + cw) * N_channels
    A_hot  = 2.0 * np.pi * R

    def residual(X: np.ndarray) -> np.ndarray:
        T_cold_wall = float(X[0])
        T_hot_wall  = float(X[1])

        if T_cold_wall < coolant_T + 1.0:
            return np.array([coolant_T + 1.0 - T_cold_wall, coolant_T + 1.0 - T_cold_wall])
        if T_cold_wall > 2000.0:
            return np.array([T_cold_wall - 2000.0, T_cold_wall - 2000.0])
        if T_hot_wall < T_cold_wall:
            return np.array([T_cold_wall - T_hot_wall, T_cold_wall - T_hot_wall])
        if T_hot_wall > T_aw:
            return np.array([T_hot_wall - T_aw, T_hot_wall - T_aw])

        wall_k, wall_k_fetch_errors = _wall_thermal_conductivity(wall_material, T_cold_wall, station_index)
        if wall_k_fetch_errors:
            errors.extend(wall_k_fetch_errors)
            return np.array([0.0, 0.0])
        
        h_coolant, cold_side_model_errors = cold_side_model(state, station_index, T_cold_wall)
        if cold_side_model_errors:
            errors.extend(cold_side_model_errors)
            return np.array([0.0, 0.0])
        
        h_gas, hot_side_model_errors = hot_side_model(state, station_index, T_hot_wall)
        if hot_side_model_errors:
            errors.extend(hot_side_model_errors)
            return np.array([0.0, 0.0])
        

        # 2D Solver Calling
        _, T_hot_wall_solution, T_cold_wall_solution = solver.steady_2d_solver(mesh, wall_k, h_gas, T_aw, h_coolant, coolant_T)

        # Equations
        eq1 = (T_hot_wall_solution - T_hot_wall)
        eq2 = (T_cold_wall_solution - T_cold_wall)

        return np.array([eq1, eq2])
    

    T_cold_wall_initial = coolant_T + 50.0
    T_hot_wall_initial  = coolant_T + 400.0
    X_initial = np.array([T_cold_wall_initial, T_hot_wall_initial])

    X_solution, _, ier, msg = fsolve(residual, X_initial, full_output=True)

    if ier != 1:
        errors.append(f"Station {station_index}: 2D wall solver did not converge — {msg}")
        return 0.0, 0.0, 0.0, errors

    T_cold_wall_solution = float(X_solution[0])
    T_hot_wall_solution  = float(X_solution[1])


    # Evaluation at solution temperatures
    wall_k, wall_k_fetch_errors = _wall_thermal_conductivity(wall_material, T_cold_wall_solution, station_index)
    if wall_k_fetch_errors:
        errors.extend(wall_k_fetch_errors)
        return 0.0, 0.0, 0.0, errors
        
    h_coolant, cold_side_model_errors = cold_side_model(state, station_index, T_cold_wall_solution)
    if cold_side_model_errors:
        errors.extend(cold_side_model_errors)
        return 0.0, 0.0, 0.0, errors
        
    h_gas, hot_side_model_errors = hot_side_model(state, station_index, T_hot_wall_solution)
    if hot_side_model_errors:
        errors.extend(hot_side_model_errors)
        return 0.0, 0.0, 0.0, errors
    

    # 2D Solver
    T_field, T_hot_wall_solution, T_cold_wall_solution = solver.steady_2d_solver(mesh, wall_k, h_gas, T_aw, h_coolant, coolant_T)

    # Heat fluxes
    Q_flux_cold = h_coolant * (T_cold_wall_solution - coolant_T) * (A_cold / A_hot)
    Q_flux_hot  = h_gas * (T_aw - T_hot_wall_solution)
    Q_flux      = (Q_flux_cold + Q_flux_hot) / 2

    state["results"]["T_field"][station_index] = T_field
    state["results"]["mesh"][station_index] = mesh

    return Q_flux, T_cold_wall_solution, T_hot_wall_solution, errors