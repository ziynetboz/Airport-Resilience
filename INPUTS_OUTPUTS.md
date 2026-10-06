# Inputs and Outputs

## Inputs

### 1. Command-line arguments (`run.py`)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--config` | path | None | Path to JSON config file. If set, model parameters are loaded from this file; `--steps` still overrides `n_steps` when not 150. |
| `--steps` | int | 150 | Number of simulation steps. |
| `--shock-at` | int | 60 | Step at which the weather shock starts. |
| `--shock-duration` | int | 12 | Duration of the shock (number of steps). |
| `--seed` | int | 42 | Random seed for reproducibility. |
| `--no-shock` | flag | False | Run without a shock (baseline run). |
| `--runs` | int | 1 | Number of independent runs (each with seed+0, seed+1, …). |
| `--output` | path | None | Output CSV path for time-series data. If set, file is written (directories created if needed). |
| `--metrics` | path | None | Output CSV path for resilience metrics (one row per run). Only used when a shock is present. |
| `--no-plot` | flag | False | Do not generate or save any plots. |
| `--plot-path` | path | `output/plots` | Directory (or path prefix) for saved plots. |

**Examples:**
```bash
python run.py
python run.py --steps 200 --shock-at 80 --output ts.csv --metrics res.csv
python run.py --config config/example_config.json --runs 5 --output runs.csv
python run.py --no-shock --no-plot
```

### 2. JSON config file (optional)

When `--config <path>` is used, the file can contain any of the following. All are optional; missing keys use defaults.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `n_steps` | int | 200 | Number of simulation steps. |
| `flights_per_step` | float | 2.5 | Mean number of new flights per step. |
| `passengers_per_flight` | [int, int] | [80, 150] | Min and max passengers per flight (uniform draw). |
| `runway_slots_per_step` | int | 5 | Runway capacity (slots per step). |
| `terminal_capacity` | int | 5000 | Terminal capacity (informational; not enforced). |
| `n_gates` | int | 100 | Total number of gates. |
| `n_airlines` | int | 3 | Number of airlines. |
| `gates_per_airline` | [int, ...] | [55, 12, 13] | Preferential gates per airline; remainder of `n_gates` are common-use. |
| `airline_flight_share` | [float, ...] | [0.8, 0.1, 0.1] | Probability that a new flight is assigned to each airline (must sum to 1). |
| `taxi_in_steps` | int | 3 | Steps to taxi from runway to gate (arrivals). |
| `taxi_out_steps` | int | 3 | Steps to taxi from gate to runway (departures). |
| `disembark_steps` | int | 3 | Steps at gate for disembarking (arrivals). |
| `board_steps` | int | 3 | Steps at gate for boarding (departures). |
| `schedule_mode` | string | `published` | `published` (STA/STD timetable + aircraft rotations) or `stochastic` (legacy injection). |
| `min_ground_time_steps` | int | 9 | Minimum ground time (MGT) after on-block before off-block. |
| `otp_on_time_tolerance_steps` | int | 1 | OTP on-time window in steps (vs STA/STD). |
| `inbound_delay_enabled` | bool | true | Draw inbound delay so ETA may exceed STA. |
| `inbound_delay_prob` | float | 0.4 | Probability an arrival has inbound delay. |
| `inbound_delay_mean_steps` | float | 2.0 | Mean inbound delay (lognormal) in steps. |
| `gdp_enabled` | bool | true | Enable Ground Delay Program (GDP / EDCT). |
| `gdp_capacity_threshold` | float | 0.7 | GDP active when capacity factor ≤ this value. |
| `irops_enabled` | bool | true | Enable airline IROPS cancellations. |
| `irops_cancel_delay_threshold_steps` | int | 15 | Cancel when projected delay ≥ this many steps. |
| `irops_max_cancels_per_step` | int | 2 | Max airline cancellations per step. |
| `n_remote_stands` | int | 10 | Remote stands (hardstands) beyond contact gates. |
| `remote_bus_transfer_steps` | int | 2 | Bus transfer time added for remote stand occupancy / taxi-out. |
| `widebody_share` | float | 0.15 | Share of flights that are widebody. |
| `widebody_gate_share` | float | 0.25 | Share of stands that are widebody class. |
| `gate_buffer_steps` | int | 1 | Minimum steps after release before reassignment. |
| `connecting_passenger_share` | float | 0.35 | Share of inbound passengers who connect (rest terminating). |
| `mct_steps` | int | 6 | Minimum Connection Time (MCT) in steps. |
| `terminal_los_enabled` | bool | true | Track terminal Level of Service (LoS). |
| `terminal_capacity_enforced` | bool | false | If true, defer terminal entry when overcrowded. |
| `los_overcrowd_mct_penalty_steps` | int | 2 | Extra MCT steps when terminal overcrowded. |
| `seed` | int or null | null | Random seed (null = unspecified). |
| `shock_at_step` | int or null | 60 | Step at which shock starts (null = no shock if using CLI --no-shock). |
| `shock_duration` | int | 12 | Duration of shock in steps. |

See `config/example_config.json` for a sample file.

### 3. Programmatic input

You can build a `SimulationConfig` (from `config`) and pass it to `AirportABM(config)`; see `config/schema.py` for the dataclass fields. Same parameter names and semantics as the JSON keys above.

---

## Outputs

### 1. Time-series CSV (`--output`)

One row per step (and per run if `--runs > 1`). Columns:

| Column | Type | Description |
|--------|------|-------------|
| `step` | int | Simulation step (0, 1, 2, …). |
| `run` | int | Run index (0 to runs−1); present only if `--runs > 1`. |
| `flights_completed` | int | Flights that landed or took off in this step. |
| `flights_cancelled` | int | Flights cancelled this step. |
| `arrival_queue` | int | Length of arrival (landing) queue. |
| `departure_queue` | int | Length of departure (takeoff) queue. |
| `weather_shock` | 0/1 | 1 if the shock is active this step, else 0. |
| `weather_capacity_factor` | float | Runway capacity factor from weather (0–1). |
| `travelers_in_terminal` | int | Number of travelers in terminal. |
| `travelers_stranded` | int | Travelers in terminal whose departure flight was cancelled. |
| `gates_available` | int | Number of gates not occupied. |
| `gate_utilization` | float | Fraction of gates in use (0–1). |
| `total_queue` | int | arrival_queue + departure_queue. |
| `effective_slots` | int | Runway slots after weather scaling. |
| `travelers_exited_this_step` | int | Travelers who exited the terminal this step. |
| `otp_arrival_pct` | float | Cumulative OTP for arrivals (ATA vs STA) at this step. |
| `otp_departure_pct` | float | Cumulative OTP for departures (ATD vs STD) at this step. |
| `gdp_active` | 0/1 | 1 if Ground Delay Program is active this step. |
| `edcts_assigned` | int | EDCTs assigned this step under GDP. |
| `flights_held_for_edct` | int | Departures waiting for EDCT this step. |
| `airline_irops_cancels` | int | Flights cancelled by airline IROPS this step. |
| `preferential_assignments` | int | Preferential gate assignments this step. |
| `common_use_assignments` | int | Common-use gate assignments this step. |
| `remote_stand_assignments` | int | Remote stand assignments this step. |
| `gate_holds` | int | Gate assignment failures this step (flight waits). |
| `travelers_misconnected` | int | Passengers who missed a connection (misconnect). |
| `connecting_in_terminal` | int | Connecting passengers still in terminal / outbound. |
| `terminal_occupancy_ratio` | float | Terminal occupancy / terminal capacity. |
| `terminal_los` | string | Level of Service letter (A–F). |
| `terminal_overcrowded` | 0/1 | 1 if occupancy exceeds terminal capacity. |

### 2. Resilience metrics CSV (`--metrics`)

One row per run. Written only when a shock is configured and `--metrics` is set. Columns:

| Column | Type | Description |
|--------|------|-------------|
| `run` | int | Run index. |
| `total_flights_completed` | int | Sum of `flights_completed` over the run. |
| `mean_throughput_per_step` | float | Mean flights completed per step. |
| `total_flights_cancelled` | int | Sum of `flights_cancelled` over the run. |
| `baseline_throughput` | float | Mean throughput in the pre-shock period. |
| `during_shock_throughput` | float | Mean throughput during the shock. |
| `throughput_drop_ratio` | float | 1 − (during_shock / baseline). |
| `recovery_step` | int or null | First step after shock where throughput ≥ 90% of baseline. |
| `recovery_time_steps` | int or null | recovery_step − shock_end_step. |
| `max_arrival_queue_during_shock` | int | Max arrival queue length during shock. |
| `max_departure_queue_during_shock` | int | Max departure queue length during shock. |
| `max_travelers_in_terminal` | int | Peak travelers in terminal over the run. |
| `stranded` | int | Count of travelers stranded (in terminal with cancelled departure) at end of run. |

### 3. Plots (unless `--no-plot`)

Saved under `--plot-path` (default `output/plots`). Directories are created if needed.

| File | Description |
|------|-------------|
| `time_series.png` | Throughput, queues, weather, travelers over time; shock interval shaded. |
| `resilience_curve.png` | Normalized throughput (relative to pre-shock baseline) over time; recovery threshold line. |
| `kpis.png` | Dashboard: resilience curve, gate utilization, total queue, stranded travelers, and Horton-aligned KPIs. |
| `metrics_summary.png` | Summary of resilience metrics (e.g. baseline vs during-shock throughput, recovery time). Only created when a shock was run and metrics were computed. |
| `run_summary.png` | Combined figure with time series and metrics summary. Only created when a shock was run. |

### 4. Console output

- Paths of any written CSV and plot files.
- When a shock is present: a printed table of the resilience metrics DataFrame (same data as in the metrics CSV if `--metrics` was set).

### 5. Return value (programmatic use)

`main()` returns the combined time-series `pd.DataFrame` (all runs concatenated, with a `run` column if `--runs > 1`), or `None` if not used programmatically.

---

## Batch runs (sensitivity and uncertainty analysis)

To run the model many times with different input distributions (e.g. different gate allocations, demand, or shock timing), use the **batch runner** and CSV-based inputs/outputs.

### Batch inputs: scenario CSV (`run_batch.py`)

**Command:**
```bash
python run_batch.py [input_csv] [--time-series-csv PATH] [--summary-csv PATH] [--runs-per-scenario N]
```

- **`input_csv`** (optional): Path to CSV with one row per scenario (default: `config/batch_input.csv`). Each row defines a full set of model parameters. Missing columns use defaults.

**Input CSV columns** (all optional; defaults in parentheses):

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `scenario_id` | any | row index | Identifier for the scenario (e.g. "base", "low_gates"). |
| `n_steps` | int | 150 | Simulation steps. |
| `flights_per_step` | float | 2.5 | Mean new flights per step. |
| `passengers_per_flight` | "min,max" | "80,150" | Min and max passengers per flight. |
| `runway_slots_per_step` | int | 5 | Runway capacity (slots per step). |
| `terminal_capacity` | int | 5000 | Terminal capacity (informational). |
| `n_gates` | int | 100 | Total gates. |
| `n_airlines` | int | 3 | Number of airlines. |
| `gates_per_airline` | "a,b,c" | "55,12,13" | Preferential gates per airline. |
| `airline_flight_share` | "a,b,c" | "0.8,0.1,0.1" | Flight share per airline (sum = 1). |
| `taxi_in_steps`, `taxi_out_steps`, `disembark_steps`, `board_steps` | int | 3 | Timing parameters. |
| `seed_base` | int | 42 | Base random seed; runs use seed_base, seed_base+1, … |
| `shock_at_step` | int or -1 | 60 | Step at which shock starts; use -1 or empty for no shock. |
| `shock_duration` | int | 12 | Duration of shock (steps). |

**CLI options:**
- `--time-series-csv`: Output path for time-series CSV (default: `output/batch_time_series.csv`).
- `--summary-csv`: Output path for summary (non–time-series) CSV (default: `output/batch_summary.csv`).
- `--runs-per-scenario`: Number of runs per scenario with different seeds (default: 1). Use > 1 for uncertainty (e.g. 10 or 100).

**Example:**
```bash
python run_batch.py
python run_batch.py config/batch_input.csv --summary-csv output/batch_summary.csv --runs-per-scenario 5
```

### Batch outputs

1. **Time-series CSV** (e.g. `output/batch_time_series.csv`)

   Same KPI columns as the single-run time-series output, plus:
   - `scenario_id`: scenario identifier from the input CSV
   - `run`: run index (0 to runs_per_scenario − 1)

   One row per (step, scenario_id, run). Use for time-dependent analysis and plots.

2. **Summary CSV** (e.g. `output/batch_summary.csv`) — for sensitivity and uncertainty

   One row per (scenario_id, run). Columns include:
   - **Inputs (repeated for convenience):** `scenario_id`, `run`, `n_steps`, `flights_per_step`, `n_gates`, `n_airlines`, `runway_slots_per_step`, `terminal_capacity`, `shock_at_step`, `shock_duration`, `seed`, `gates_per_airline`, `airline_flight_share`
   - **Output metrics (non–time-series):** `total_flights_completed`, `mean_throughput_per_step`, `total_flights_cancelled`, `baseline_throughput`, `during_shock_throughput`, `throughput_drop_ratio`, `recovery_step`, `recovery_time_steps`, `max_arrival_queue_during_shock`, `max_departure_queue_during_shock`, `max_travelers_in_terminal`, `mean_travelers_in_terminal`, `stranded`

   Use this file to:
   - Run **sensitivity analysis**: vary one or more input columns and plot or regress summary metrics (e.g. `throughput_drop_ratio`, `recovery_time_steps`) vs inputs.
   - Run **uncertainty analysis**: for each scenario, use multiple runs (`--runs-per-scenario`) and summarize distributions (mean, percentiles) of the output metrics.

   No extra plotting script is required; use your preferred tool (e.g. pandas, R, Excel) on the summary CSV.
