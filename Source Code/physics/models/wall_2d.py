from scipy.sparse.linalg import spsolve
from scipy.interpolate import interp1d
from scipy.sparse import lil_matrix
from scipy.optimize import fsolve
import numpy as np

from core.geometry import generate_mesh

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


# ── Laplacian Matrix ───────────────────────────────────────────────────────────────
def _build_interior_laplacian(mask: np.ndarray, index_map: np.ndarray, n_dofs: int, kx: float, ky: float) -> lil_matrix:
    nx, ny = mask.shape
    A      = lil_matrix((n_dofs, n_dofs))

    for i in range(nx):
        for j in range(ny):
            if not mask[i, j]:
                continue

            p = index_map[i, j]

            for di, dj in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                ni, nj    = i + di, j + dj
                k_coeff   = kx if di != 0 else ky

                # only wall-to-wall connections here
                if 0 <= ni < nx and 0 <= nj < ny and mask[ni, nj]:
                    q          = index_map[ni, nj]
                    A[p, q]   += k_coeff
                    A[p, p]   -= k_coeff

    return A


# ── Boundary Conditions ───────────────────────────────────────────────────────────────
def _apply_boundary_conditions(
    A         : lil_matrix,
    b         : np.ndarray,
    mask      : np.ndarray,
    index_map : np.ndarray,
    dx        : float,
    dy        : float,
    h_gas     : float,
    T_aw      : float,
    h_coolant : float,
    coolant_T : float,
) -> None:
    nx, ny = mask.shape

    for i in range(nx):
        for j in range(ny):
            if not mask[i, j]:
                continue

            p = index_map[i, j]

            for di, dj in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                ni, nj  = i + di, j + dj
                ds      = dx if di != 0 else dy

                # ── out-of-bounds faces ───────────────────────────────────
                if not (0 <= ni < nx and 0 <= nj < ny):

                    if dj == -1 and j == 0:
                        # bottom edge → hot gas Robin
                        A[p, p] -= h_gas / dy
                        b[p]    -= h_gas / dy * T_aw

                    # top (dj == +1, j == ny-1) → adiabatic, do nothing
                    # left (di == -1, i == 0)   → adiabatic, do nothing
                    # right (di == +1, i == nx-1)→ adiabatic, do nothing

                # ── channel neighbour ─────────────────────────────────────
                elif not mask[ni, nj]:
                    # The right boundary (i == nx-1) is the symmetry plane.
                    # If the channel node sits exactly at the right boundary
                    # that face belongs to symmetry → adiabatic, do nothing.
                    if ni == nx - 1 and di == 1:
                        pass
                    else:
                        # all other channel faces → coolant Robin
                        A[p, p] -= h_coolant / ds
                        b[p]    -= h_coolant / ds * coolant_T


# ── 2D Linear Solver ───────────────────────────────────────────────────────────────
def steady_2d_solver(mesh: dict, wall_k: float, h_gas: float, T_aw: float, h_coolant: float, coolant_T: float) -> tuple[np.ndarray, float, float]:
    """
    Solves the steady 2-D heat conduction problem in the wall cross-section.
    """
    nx, ny = mesh["nx"], mesh["ny"]
    mask   = mesh["mask"]
    x, y   = mesh["x"], mesh["y"]
    dx     = x[1] - x[0]
    dy     = y[1] - y[0]

    kx = wall_k / dx**2
    ky = wall_k / dy**2

    # ── DOF map ───────────────────────────────────────────────────────────────
    index_map = mesh["index_map"]
    n_dofs = int(index_map.max()) + 1

    # ── System Assembly ───────────────────────────────────────────────────────
    A = _build_interior_laplacian(mask, index_map, n_dofs, kx, ky)
    b = np.zeros(n_dofs)

    _apply_boundary_conditions(
        A         = A,
        b         = b,
        mask      = mask,
        index_map = index_map,
        dx        = dx,
        dy        = dy,
        h_gas     = h_gas,
        T_aw      = T_aw,
        h_coolant = h_coolant,
        coolant_T = coolant_T,
    )

    # ── Solve ─────────────────────────────────────────────────────────────────
    temperature_field_flat = spsolve(A.tocsc(), b)

    # ── reconstruct 2-D field ─────────────────────────────────────────────────
    temperature_field = np.full((nx, ny), np.nan)
    for i in range(nx):
        for j in range(ny):
            if index_map[i, j] >= 0:
                temperature_field[i, j] = temperature_field_flat[index_map[i, j]]

    # ── T_hot_wall : mean of j=0 wall nodes ──────────────────────────────────
    hot_wall_values = [temperature_field[i, 0] for i in range(nx) if mask[i, 0]]
    T_hot_wall = float(np.mean(hot_wall_values))

    # ── T_cold_wall : mean of wall nodes touching any coolant Robin face ──────
    # A node qualifies if it has at least one channel neighbour that is NOT
    # on the right symmetry boundary (those faces are adiabatic, not coolant).
    cold_wall_values = []
    for i in range(nx):
        for j in range(ny):
            if not mask[i, j]:
                continue
            for di, dj in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                ni, nj = i + di, j + dj
                if not (0 <= ni < nx and 0 <= nj < ny):
                    continue
                if not mask[ni, nj]:                    # channel neighbour
                    if ni == nx - 1 and di == 1:        # right-boundary face → skip
                        continue
                    cold_wall_values.append(temperature_field[i, j])
                    break   # count this wall node once even if it has 2 coolant faces
    T_cold_wall = float(np.mean(cold_wall_values))

    return temperature_field, T_hot_wall, T_cold_wall



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
        

        # 2D Solver
        _, T_hot_wall_solution, T_cold_wall_solution = steady_2d_solver(mesh, wall_k, h_gas, T_aw, h_coolant, coolant_T)

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
    T_field, T_hot_wall_solution, T_cold_wall_solution = steady_2d_solver(mesh, wall_k, h_gas, T_aw, h_coolant, coolant_T)

    # Heat fluxes
    Q_flux_cold = h_coolant * (T_cold_wall_solution - coolant_T) * (A_cold / A_hot)
    Q_flux_hot  = h_gas * (T_aw - T_hot_wall_solution)
    Q_flux      = (Q_flux_cold + Q_flux_hot) / 2

    state["results"]["T_field"][station_index] = T_field
    state["results"]["mesh"][station_index] = mesh

    return Q_flux, T_cold_wall_solution, T_hot_wall_solution, errors