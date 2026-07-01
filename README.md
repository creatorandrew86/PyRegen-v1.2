# PyRegen v1.2

**Regenerative cooling analysis software for small and medium scale liquid-propellant rocket chambers and nozzles.**

PyRegen computes the thermal and hydraulic behaviour of a regeneratively cooled rocket engine. Given engine operating conditions, nozzle geometry, coolant properties, and cooling channel geometry, it solves the coupled heat transfer problem station by station along the nozzle wall, producing wall temperatures, heat flux, and coolant state at each station, with support for both 1D and 2D wall conduction models.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Dependencies](#dependencies)
- [Installation](#installation)
- [Usage](#usage)
- [Inputs](#inputs)
- [Wall Models](#wall-models)
- [Outputs](#outputs)
- [State Structure](#state-structure)
- [License](#license)

---

## Features

- CEA integration for combustion gas properties (temperature, specific heat ratio, Prandtl number, viscosity, Mach number)
- Conical and bell nozzle contour generation with configurable resolution
- Station-by-station regenerative cooling solver
- Coolant thermodynamic and transport property lookup via CoolProp
- Cooling channel geometry defined via control points with linear or cubic spline interpolation
- Gas-side and coolant-side heat transfer coefficient computation via a swappable model registry
- Selectable 1D (fin-effect) or 2D wall conduction models
- Coolant-side pressure drop modelling
- Heat flux and wall temperature distribution along the nozzle
- File export of per-station results
- Graphical output: nozzle profile viewer, configurable x/y plots of all computed quantities, and a summary results window
- Modular UI with dynamic layout, callback-driven updates, and themeable interface

---

## Project Structure

```
PyRegen-v1.2/
├── assets/
│   ├── __init__.py
│   ├── data.py                      # Static asset loading helpers
│   ├── Inter-VariableFont_opsz...   # UI font
│   ├── NozzleData.json              # Reference nozzle geometry data
│   └── ThermalConductivity...json   # Wall material conductivity data
├── core/
│   ├── cea.py                       # CEA calls and gas property computation
│   ├── constants.py                 # Physical and unit conversion constants
│   ├── geometry.py                  # Nozzle contour and channel geometry
│   ├── input.py                     # Input validation and preprocessing
│   └── state.py                     # State initialisation and management
├── output/
│   ├── __init__.py
│   ├── files.py                     # Per-station result file export
│   ├── graphs.py                    # Plot generation
│   └── output.py                    # Output orchestration and summary results
├── physics/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── cold_side_models.py      # Coolant-side heat transfer correlations
│   │   ├── hot_side_models.py       # Gas-side heat transfer correlations
│   │   ├── pressure_drop_models.py  # Coolant pressure drop correlations
│   │   ├── registry.py              # Model registration and lookup
│   │   ├── wall_1d.py               # 1D through-wall conduction model
│   │   └── wall_2d.py               # 2D fin-effect / channel cross-section conduction model
│   ├── __init__.py
│   └── solver.py                    # Station-by-station cooling solver
├── ui/
│   ├── __init__.py
│   ├── callbacks.py                 # User interaction callbacks
│   ├── dynamic.py                   # Dynamic widget/layout updates
│   ├── layout.py                    # GUI layout definition
│   ├── messages.py                  # Status and error messaging
│   ├── run.py                       # Analysis run orchestration
│   └── themes.py                    # GUI theming
├── main.py                          # Entry point, DearPyGui event loop
├── .gitignore
├── LICENSE
└── README.md
```

---

## Dependencies

| Package | Purpose |
|---|---|
| Python 3.10+ | Runtime |
| [RocketCEA](https://rocketcea.readthedocs.io/) | CEA wrapper for combustion gas properties |
| [CoolProp](http://www.coolprop.org/) | Coolant thermodynamic and transport properties |
| [DearPyGui](https://github.com/hoffstadt/DearPyGui) | GUI and plotting |
| NumPy | Numerical arrays |
| SciPy | Channel geometry control point interpolation and 2D conduction solve |

---

## Installation

1. Clone the repository:
```bash
   git clone https://github.com/creatorandrew86/PyRegen-v1.2.git
   cd PyRegen-v1.2
```

2. Install dependencies:
```bash
   pip install rocketcea coolprop dearpygui numpy scipy
```

> **Note:** RocketCEA requires NASA CEA to be installed separately. See the [RocketCEA documentation](https://rocketcea.readthedocs.io/en/latest/installCEA.html) for instructions.

---

## Usage

```bash
python main.py
```

Once the GUI opens, follow these steps:

1. Set **engine parameters** and run CEA to compute combustion gas properties
2. Define **nozzle geometry** and generate the contour
3. Set **coolant** and **channel parameters**
4. Choose the **wall conduction model** (1D or 2D) and gas/coolant-side correlations
5. Run the **solver**
6. Use the **Output** section to generate plots, export result files, or view the summary results window

---

## Inputs

### Engine Parameters
- Oxidizer and fuel selection
- Chamber pressure (Pc)
- Mixture ratio (MR)
- Mass flow rate or throat radius (Rt)

### Nozzle Parameters
- Contraction ratio (CR), expansion ratio (ε), characteristic length (L*)
- Nozzle type (conical / bell), length percentage, wall angle, contour resolution

### Coolant Parameters
- Coolant fluid selection
- Mass flow rate, inlet temperature, inlet pressure

### Channel Parameters
- Wall material and thickness
- Number of cooling channels
- Channel width and height control points (axial position, `cw`, `ch`)
- Interpolation type (linear / cubic spline), jacket resolution

### Solver Options
- Gas-side heat transfer correlation
- Coolant-side heat transfer correlation
- Pressure drop correlation
- Wall conduction model (1D or 2D)

---

## Wall Models

PyRegen supports two selectable wall conduction models, both accessed through the model registry:

- **1D model (`wall_1d.py`)** — treats the wall as a simple through-thickness conduction path between the hot gas side and coolant side, with added fin-effect corerctions. Faster, but less accurate, optimal for preliminary design and iteration.
- **2D model (`wall_2d.py`)** — resolves conduction across the channel cross-section. Produces a more accurate hot wall temperature distribution and land-tip temperature, at the cost of additional solve time per station.

The wall model is selected alongside the gas-side and coolant-side heat transfer correlations before running the solver, and results from either model populate the same per-station output arrays.

---

## Outputs

### Per-Station Arrays
| Quantity | Description |
|---|---|
| Axial position, radius, area ratio | Nozzle geometry at each station |
| Gas temperature, adiabatic wall temperature | Hot-gas thermal conditions |
| Mach number, gamma | Flow properties |
| Cold wall temp, hot wall temp | Wall thermal state (1D or 2D, per selected model) |
| Land-tip temperature | Fin-effect temperature (2D model only) |
| Heat flux | Local heat flux (W/m²) |
| Gas-side HTC, coolant-side HTC | Heat transfer coefficients |
| Coolant temperature, pressure, enthalpy | Coolant thermodynamic state |
| Coolant density, velocity, thermal conductivity | Coolant transport properties |
| Reynolds number, Prandtl number | Coolant flow regime |
| Channel width, height, land width, hydraulic diameter, flow area | Channel geometry |

### Summary Results
- Maximum heat flux (MW/m²)
- Maximum hot wall temperature (K)
- Coolant pressure drop (bar)
- Coolant temperature rise (K)

### File Export
- Per-station results exportable to file via the Output section for use in downstream analysis or reporting

---

## State Structure

All data is held in a single `state` dictionary, initialised via `make_state()` and populated progressively as each analysis stage runs:

```
state
├── engine_parameters
├── nozzle_parameters
├── coolant_parameters
├── channel_parameters
├── solver_options
└── results
```

---

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for details.
