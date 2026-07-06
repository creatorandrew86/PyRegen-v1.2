#include <iostream>
#include <vector>
#include <tuple>
#include <cmath>
#include <numeric>
#include <stdexcept>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include <Eigen/Sparse>
#include <Eigen/SparseLU>

namespace py = pybind11;

using Matrix   = std::vector<std::vector<double>>;
using BoolGrid = std::vector<std::vector<bool>>;
using IntGrid  = std::vector<std::vector<int>>;
using SpMat    = Eigen::SparseMatrix<double>;
using Triplet  = Eigen::Triplet<double>;

// ── Mesh struct ─────────────────────────────────────────────────────────────
struct Mesh {
    int nx = 0;
    int ny = 0;
    std::vector<double> x;
    std::vector<double> y;
    BoolGrid mask;
    IntGrid  index_map;
};

// ── Laplacian Matrix ───────────────────────────────────────────────────────────────
// Builds the interior conduction stencil (wall-to-wall connections only) as a
// list of triplets, equivalent to the Python lil_matrix accumulation.
static void _build_interior_laplacian(
    const BoolGrid& mask,
    const IntGrid&  index_map,
    int n_dofs,
    double kx,
    double ky,
    std::vector<Triplet>& triplets
) {
    int nx = static_cast<int>(mask.size());
    int ny = nx > 0 ? static_cast<int>(mask[0].size()) : 0;

    // diagonal accumulator so we emit a single triplet per (p,p) entry
    std::vector<double> diag(n_dofs, 0.0);

    static const int deltas[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    for (int i = 0; i < nx; ++i) {
        for (int j = 0; j < ny; ++j) {
            if (!mask[i][j]) continue;

            int p = index_map[i][j];

            for (const auto& d : deltas) {
                int di = d[0], dj = d[1];
                int ni = i + di, nj = j + dj;
                double k_coeff = (di != 0) ? kx : ky;

                // only wall-to-wall connections here
                if (ni >= 0 && ni < nx && nj >= 0 && nj < ny && mask[ni][nj]) {
                    int q = index_map[ni][nj];
                    triplets.emplace_back(p, q, k_coeff);
                    diag[p] -= k_coeff;
                }
            }
        }
    }

    for (int p = 0; p < n_dofs; ++p) {
        if (diag[p] != 0.0) {
            triplets.emplace_back(p, p, diag[p]);
        }
    }
}

// ── Boundary Conditions ───────────────────────────────────────────────────────────────
// Appends Robin BC contributions (hot-gas + coolant) to the triplet list and
// accumulates the RHS vector b in place, equivalent to the Python version's
// direct A[p, p] -= ... / b[p] -= ... updates.
static void _apply_boundary_conditions(
    std::vector<Triplet>& triplets,
    Eigen::VectorXd& b,
    const BoolGrid& mask,
    const IntGrid&  index_map,
    double dx,
    double dy,
    double h_gas,
    double T_aw,
    double h_coolant,
    double coolant_T
) {
    int nx = static_cast<int>(mask.size());
    int ny = nx > 0 ? static_cast<int>(mask[0].size()) : 0;

    static const int deltas[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    for (int i = 0; i < nx; ++i) {
        for (int j = 0; j < ny; ++j) {
            if (!mask[i][j]) continue;

            int p = index_map[i][j];

            for (const auto& d : deltas) {
                int di = d[0], dj = d[1];
                int ni = i + di, nj = j + dj;
                double ds = (di != 0) ? dx : dy;

                bool in_bounds = (ni >= 0 && ni < nx && nj >= 0 && nj < ny);

                // ── out-of-bounds faces ───────────────────────────────────
                if (!in_bounds) {
                    if (dj == -1 && j == 0) {
                        // bottom edge → hot gas Robin
                        triplets.emplace_back(p, p, -h_gas / dy);
                        b[p] -= h_gas / dy * T_aw;
                    }
                    // top (dj == +1, j == ny-1) → adiabatic, do nothing
                    // left (di == -1, i == 0)   → adiabatic, do nothing
                    // right (di == +1, i == nx-1)→ adiabatic, do nothing

                // ── channel neighbour ─────────────────────────────────────
                } else if (!mask[ni][nj]) {
                    // The right boundary (i == nx-1) is the symmetry plane.
                    // If the channel node sits exactly at the right boundary
                    // that face belongs to symmetry → adiabatic, do nothing.
                    if (ni == nx - 1 && di == 1) {
                        // symmetry → do nothing
                    } else {
                        // all other channel faces → coolant Robin
                        triplets.emplace_back(p, p, -h_coolant / ds);
                        b[p] -= h_coolant / ds * coolant_T;
                    }
                }
            }
        }
    }
}

// ── 2D Linear Solver ───────────────────────────────────────────────────────────────
std::tuple<Matrix, double, double> steady_2d_solver(
    const Mesh& mesh,
    double wall_k,
    double h_gas,
    double T_aw,
    double h_coolant,
    double coolant_T
) {
    int nx = mesh.nx, ny = mesh.ny;
    const BoolGrid& mask = mesh.mask;
    const std::vector<double>& x = mesh.x;
    const std::vector<double>& y = mesh.y;

    if (nx < 2 || ny < 2) {
        throw std::invalid_argument("mesh must have nx >= 2 and ny >= 2");
    }

    double dx = x[1] - x[0];
    double dy = y[1] - y[0];

    double kx = wall_k / (dx * dx);
    double ky = wall_k / (dy * dy);

    // ── DOF map ───────────────────────────────────────────────────────────────
    const IntGrid& index_map = mesh.index_map;
    int n_dofs = 0;
    for (int i = 0; i < nx; ++i)
        for (int j = 0; j < ny; ++j)
            n_dofs = std::max(n_dofs, index_map[i][j] + 1);

    // ── System Assembly ───────────────────────────────────────────────────────
    std::vector<Triplet> triplets;
    triplets.reserve(static_cast<size_t>(n_dofs) * 5);

    _build_interior_laplacian(mask, index_map, n_dofs, kx, ky, triplets);

    Eigen::VectorXd b = Eigen::VectorXd::Zero(n_dofs);

    _apply_boundary_conditions(
        triplets,
        b,
        mask,
        index_map,
        dx,
        dy,
        h_gas,
        T_aw,
        h_coolant,
        coolant_T
    );

    SpMat A(n_dofs, n_dofs);
    A.setFromTriplets(triplets.begin(), triplets.end());
    A.makeCompressed();

    // ── Solve ─────────────────────────────────────────────────────────────────
    Eigen::SparseLU<SpMat> solver;
    solver.analyzePattern(A);
    solver.factorize(A);
    if (solver.info() != Eigen::Success) {
        throw std::runtime_error("SparseLU factorization failed");
    }
    Eigen::VectorXd temperature_field_flat = solver.solve(b);
    if (solver.info() != Eigen::Success) {
        throw std::runtime_error("SparseLU solve failed");
    }

    // ── reconstruct 2-D field ─────────────────────────────────────────────────
    Matrix temperature_field(nx, std::vector<double>(ny, std::nan("")));
    for (int i = 0; i < nx; ++i) {
        for (int j = 0; j < ny; ++j) {
            if (index_map[i][j] >= 0) {
                temperature_field[i][j] = temperature_field_flat[index_map[i][j]];
            }
        }
    }

    // ── T_hot_wall : mean of j=0 wall nodes ──────────────────────────────────
    std::vector<double> hot_wall_values;
    for (int i = 0; i < nx; ++i) {
        if (mask[i][0]) {
            hot_wall_values.push_back(temperature_field[i][0]);
        }
    }
    double T_hot_wall = hot_wall_values.empty()
        ? std::nan("")
        : std::accumulate(hot_wall_values.begin(), hot_wall_values.end(), 0.0) / hot_wall_values.size();

    // ── T_cold_wall : mean of wall nodes touching any coolant Robin face ──────
    // A node qualifies if it has at least one channel neighbour that is NOT
    // on the right symmetry boundary (those faces are adiabatic, not coolant).
    static const int deltas[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    std::vector<double> cold_wall_values;
    for (int i = 0; i < nx; ++i) {
        for (int j = 0; j < ny; ++j) {
            if (!mask[i][j]) continue;
            for (const auto& d : deltas) {
                int di = d[0], dj = d[1];
                int ni = i + di, nj = j + dj;
                if (!(ni >= 0 && ni < nx && nj >= 0 && nj < ny)) continue;
                if (!mask[ni][nj]) {                     // channel neighbour
                    if (ni == nx - 1 && di == 1) continue;  // right-boundary face → skip
                    cold_wall_values.push_back(temperature_field[i][j]);
                    break;  // count this wall node once even if it has 2 coolant faces
                }
            }
        }
    }
    double T_cold_wall = cold_wall_values.empty()
        ? std::nan("")
        : std::accumulate(cold_wall_values.begin(), cold_wall_values.end(), 0.0) / cold_wall_values.size();

    return std::make_tuple(temperature_field, T_hot_wall, T_cold_wall);
}

// ── pybind11 glue ────────────────────────────────────────────────────────────────
// Converts a Python dict (matching the Python `generate_mesh` output) into a Mesh,
// so the C++ solver can be called with mesh = generate_mesh(...) from Python,
// regardless of whether generate_mesh itself is the Python or the C++ version below.
static Mesh mesh_from_pydict(const py::dict& d) {
    Mesh mesh;
    mesh.nx = d["nx"].cast<int>();
    mesh.ny = d["ny"].cast<int>();

    auto x_arr = d["x"].cast<py::array_t<double>>();
    auto y_arr = d["y"].cast<py::array_t<double>>();
    mesh.x.assign(x_arr.data(), x_arr.data() + x_arr.size());
    mesh.y.assign(y_arr.data(), y_arr.data() + y_arr.size());

    auto mask_arr = d["mask"].cast<py::array_t<bool>>();
    auto idx_arr  = d["index_map"].cast<py::array_t<long>>();

    auto mask_u = mask_arr.unchecked<2>();
    auto idx_u  = idx_arr.unchecked<2>();

    int nx = mesh.nx, ny = mesh.ny;
    mesh.mask.assign(nx, std::vector<bool>(ny, true));
    mesh.index_map.assign(nx, std::vector<int>(ny, -1));

    for (int i = 0; i < nx; ++i) {
        for (int j = 0; j < ny; ++j) {
            mesh.mask[i][j]      = mask_u(i, j);
            mesh.index_map[i][j] = static_cast<int>(idx_u(i, j));
        }
    }

    return mesh;
}

// Python-facing wrapper: accepts a dict (as produced by the Python
// `generate_mesh`) so the call site `steady_2d_solver(mesh, ...)` is unchanged.
static std::tuple<Matrix, double, double> steady_2d_solver_py(
    const py::dict& mesh_dict,
    double wall_k,
    double h_gas,
    double T_aw,
    double h_coolant,
    double coolant_T
) {
    Mesh mesh = mesh_from_pydict(mesh_dict);
    return steady_2d_solver(mesh, wall_k, h_gas, T_aw, h_coolant, coolant_T);
}

PYBIND11_MODULE(steady_2d_solver, m) {
    m.def("steady_2d_solver", &steady_2d_solver_py,
          "2D steady heat equation solver with convection boundaries",
          py::arg("mesh"),
          py::arg("wall_k"),
          py::arg("h_gas"),
          py::arg("T_aw"),
          py::arg("h_coolant"),
          py::arg("coolant_T"));
}