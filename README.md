# Airport Resilience ABM

Agent-based model of **airport operations**, **traveler activities**, and **weather-driven shocks**. Includes **taxi time**, **gate assignments by airlines**, and **gate availability**. Default configuration: ~100 gates, 3 airlines (unequal gate and flight shares), 5 runway slots, 2.5 flights/step. Designed for **resilience** analysis: how throughput, queues, gate utilization, and stranding behave during and after a shock. All parameters are configurable; no real-world airport is referenced.

**Documentation:**
- [INPUTS_OUTPUTS.md](INPUTS_OUTPUTS.md) — Inputs (CLI, config file, parameters) and outputs (CSVs, plots)
- [docs/MODEL_DOCUMENTATION.md](docs/MODEL_DOCUMENTATION.md) — Theoretical basis, assumptions, and implementation explanation
- [ODD.md](ODD.md) — Full ODD (Overview, Design concepts, and Details) protocol description
- [docs/REALISM_GAP_ANALYSIS.md](docs/REALISM_GAP_ANALYSIS.md) — Prioritized gaps for operational realism (gates, delays, cancellations, schedule, baggage)
- [docs/PUBLISHED_SCHEDULE_AND_OTP.md](docs/PUBLISHED_SCHEDULE_AND_OTP.md) — Published flight schedule, aircraft rotations (MGT), STA/STD, and OTP
- [docs/INBOUND_DELAY_GDP_IROPS.md](docs/INBOUND_DELAY_GDP_IROPS.md) — Inbound delay (ETA), Ground Delay Program (GDP / EDCT), airline IROPS
- [docs/GATE_ALLOCATION.md](docs/GATE_ALLOCATION.md) — Preferential / common-use gates, remote stands, gate class
- [docs/CONNECTIONS_MCT_TERMINAL_LOS.md](docs/CONNECTIONS_MCT_TERMINAL_LOS.md) — Connecting passengers (MCT), misconnects, terminal Level of Service (LoS)
- [docs/BAGGAGE_HANDLING.md](docs/BAGGAGE_HANDLING.md) — Transfer bags, make-up, claim, mishandled bags, bag-induced departure hold

## Design

- **Object-oriented**: Clear separation of agents, model, config, and metrics.
- **Parameterization**: All parameters live in the `config` package (schema + defaults).
- **Modular Python files**: One main responsibility per module for maintainability.

## Layout

```
config/             # Parameterization
  __init__.py
  schema.py         # Dataclasses: ModelConfig, SimulationConfig, etc.
  defaults.py       # Default instances and build_simulation_config()
  loader.py         # load_simulation_config(), load_run_config()
  example_config.json   # Example JSON config for run.py --config
  batch_input.csv   # Example scenario CSV for run_batch.py
agents/             # Entities
  __init__.py
  weather_constants.py   # WeatherCondition enum, capacity factors
  weather.py             # WeatherAgent
  flight.py              # Flight, FlightType, FlightState
  gate.py                # Gate, GatePool (airline assignments)
  airport.py             # Airport (runway, terminal, gates)
  traveler.py            # Traveler, TravelerState
model/               # Core ABM
  __init__.py
  abm.py             # AirportABM (orchestrator)
  step_runner.py     # StepRunner (order of operations each step)
  flight_scheduler.py    # FlightScheduler (new flights + travelers per step)
metrics/
  __init__.py
  collectors.py      # create_data_collector() — model reporters
  resilience.py      # compute_resilience_metrics(), summarize_runs()
viz/
  __init__.py
  export.py          # export_time_series(), export_metrics() — CSV output
  plots.py           # plot_time_series(), plot_resilience_curve(), plot_kpis(), etc.
run.py               # CLI entry point (single runs)
run_batch.py         # Batch runner (CSV in → time-series + summary CSVs)
requirements.txt
README.md
INPUTS_OUTPUTS.md
ODD.md
LICENSE
docs/
  MODEL_DOCUMENTATION.md
```

## Setup

```bash
git clone <your-repo-url>
cd Airport-Resilience
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
# With shock at step 60, duration 12
python run.py

# No shock (baseline)
python run.py --no-shock

# Custom shock and output
python run.py --steps 200 --shock-at 80 --shock-duration 15 --output ts.csv --metrics res.csv

# Multiple runs
python run.py --runs 5 --output runs.csv --metrics resilience.csv

# Plots are generated automatically (saved to output/plots/ by default)
python run.py
python run.py --plot-path results/figs

# Skip generating plots
python run.py --no-plot
```

### Batch runs (sensitivity and uncertainty analysis)

To run many scenarios with different parameter distributions, use a **scenario CSV** as input and write **time-series** and **summary** CSVs:

```bash
python run_batch.py
python run_batch.py config/batch_input.csv --summary-csv output/batch_summary.csv --runs-per-scenario 5
```

- **Input:** CSV with one row per scenario (default: `config/batch_input.csv`). Columns: `n_steps`, `flights_per_step`, `gates_per_airline`, `shock_at_step`, etc. See [INPUTS_OUTPUTS.md](INPUTS_OUTPUTS.md#batch-runs-sensitivity-and-uncertainty-analysis).
- **Output 1:** Time-series CSV with KPI columns plus `scenario_id` and `run`.
- **Output 2:** Summary CSV (one row per scenario/run) with inputs and derived metrics for sensitivity/uncertainty analysis (e.g. throughput drop, recovery time, stranded).

## Visualization and data export

The **`viz`** module handles CSV export and plotting:

- **Export** (`viz/export.py`): `export_time_series(df, path)` and `export_metrics(metrics_df, path)` write CSV files (directories are created if needed).
- **Plots** (`viz/plots.py`): `plot_time_series()` (throughput, queues, weather, travelers), `plot_resilience_curve()` (normalized throughput over time—drop and recovery), `plot_kpis()` (resilience curve, gate utilization, total queue, stranded travelers), `plot_metrics_summary()` (baseline vs during-shock throughput, recovery time), `plot_run_summary()` (combined figure). Requires `matplotlib`.

Plots are **generated automatically** every time you run `run.py`. Use `--no-plot` to skip them; use `--plot-path` to change the output directory (default: `output/plots`).

## Configuration

- **Schema** (`config/schema.py`): `ModelConfig`, `WeatherConfig`, `AirportConfig`, `ShockConfig`, `RunConfig`, `SimulationConfig`.
- **Defaults** (`config/defaults.py`): `get_default_config()`, `get_baseline_config()`, `build_simulation_config()`.
- **File loader** (`config/loader.py`): `load_simulation_config(path)` reads JSON; see `config/example_config.json`. Use for parameterization in a separate file.
- Override via CLI in `run.py`, or build `SimulationConfig` in code and pass to `AirportABM(config)`.

## Resilience Metrics

Computed in `metrics/resilience.py`: throughput (baseline, during shock, drop ratio), recovery time (steps to ≥90% baseline), max queues during shock, travelers in terminal / stranded.

## Extending

- Add or tune parameters in `config/schema.py` and `config/defaults.py`.
- Add agents in `agents/` and wire them in `model/step_runner.py` and `model/abm.py`.
- Add reporters in `metrics/collectors.py` and metrics in `metrics/resilience.py`.
- Add export formats in `viz/export.py` and new figures in `viz/plots.py`.

## License

MIT License. See [LICENSE](LICENSE).
