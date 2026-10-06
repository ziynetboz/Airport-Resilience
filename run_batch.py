#!/usr/bin/env python3
"""
Batch runner: run the model for each row of an input CSV, write time-series and
summary CSVs for sensitivity and uncertainty analysis.
"""

import argparse
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from config import get_default_config, SimulationConfig
from config.schedule_mode import ScheduleMode
from config.copy_config import copy_simulation_config
from config.schema import DEFAULT_GATES_PER_AIRLINE, DEFAULT_AIRLINE_FLIGHT_SHARE
from model import AirportABM
from metrics import compute_resilience_metrics
from viz import export_time_series, export_metrics


def _parse_tuple_int(s: str, default: tuple) -> tuple:
    """Parse '70,15,15' -> (70, 15, 15)."""
    if s is None or (isinstance(s, float) and pd.isna(s)) or str(s).strip() == "":
        return default
    parts = [int(x.strip()) for x in str(s).split(",") if x.strip()]
    return tuple(parts) if parts else default


def _parse_tuple_float(s: str, default: tuple) -> tuple:
    """Parse '0.8,0.1,0.1' -> (0.8, 0.1, 0.1)."""
    if s is None or (isinstance(s, float) and pd.isna(s)) or str(s).strip() == "":
        return default
    parts = [float(x.strip()) for x in str(s).split(",") if x.strip()]
    return tuple(parts) if parts else default


def _parse_passengers(s: Any) -> tuple:
    """Parse passengers_per_flight: '80,150' or two columns min,max."""
    if s is None or (isinstance(s, float) and pd.isna(s)) or str(s).strip() == "":
        return (80, 150)
    parts = [int(x.strip()) for x in str(s).split(",") if x.strip()]
    if len(parts) >= 2:
        return (parts[0], parts[1])
    return (80, 150)


def row_to_config(row: pd.Series, default_cfg: SimulationConfig) -> SimulationConfig:
    """Build SimulationConfig from a CSV row. Missing columns use defaults."""
    def get(key: str, default: Any) -> Any:
        if key not in row.index:
            return default
        v = row[key]
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return default
        return v

    n_steps = int(get("n_steps", 150))
    flights_per_step = float(get("flights_per_step", 2.5))
    passengers = _parse_passengers(get("passengers_per_flight", "80,150"))
    runway_slots = int(get("runway_slots_per_step", 5))
    terminal_capacity = int(get("terminal_capacity", 5000))
    n_gates = int(get("n_gates", 100))
    n_airlines = int(get("n_airlines", 3))
    taxi_in = int(get("taxi_in_steps", 3))
    taxi_out = int(get("taxi_out_steps", 3))
    disembark = int(get("disembark_steps", 3))
    board = int(get("board_steps", 3))
    gates_per_airline = _parse_tuple_int(
        get("gates_per_airline", "70,15,15"), DEFAULT_GATES_PER_AIRLINE
    )
    airline_flight_share = _parse_tuple_float(
        get("airline_flight_share", "0.8,0.1,0.1"), DEFAULT_AIRLINE_FLIGHT_SHARE
    )
    seed_val = get("seed_base", 42)
    shock_at_raw = get("shock_at_step", 60)
    if shock_at_raw is None or (isinstance(shock_at_raw, float) and pd.isna(shock_at_raw)):
        shock_at = 60  # default
    elif str(shock_at_raw).strip() in ("", "-", "-1"):
        shock_at = None  # no shock
    else:
        try:
            v = int(float(shock_at_raw))
            shock_at = None if v < 0 else v
        except (ValueError, TypeError):
            shock_at = 60
    shock_duration = int(get("shock_duration", 12))
    schedule_mode_raw = str(get("schedule_mode", default_cfg.schedule_mode.value))
    schedule_mode = ScheduleMode(schedule_mode_raw)
    min_ground_time_steps = int(get("min_ground_time_steps", default_cfg.min_ground_time_steps))
    otp_tol = int(get("otp_on_time_tolerance_steps", default_cfg.otp_on_time_tolerance_steps))

    return SimulationConfig(
        n_steps=n_steps,
        flights_per_step=flights_per_step,
        passengers_per_flight=passengers,
        runway_slots_per_step=runway_slots,
        terminal_capacity=terminal_capacity,
        n_gates=n_gates,
        n_airlines=n_airlines,
        taxi_in_steps=taxi_in,
        taxi_out_steps=taxi_out,
        disembark_steps=disembark,
        board_steps=board,
        gates_per_airline=gates_per_airline,
        airline_flight_share=airline_flight_share,
        schedule_mode=schedule_mode,
        min_ground_time_steps=min_ground_time_steps,
        otp_on_time_tolerance_steps=otp_tol,
        inbound_delay_enabled=bool(get("inbound_delay_enabled", default_cfg.inbound_delay_enabled)),
        inbound_delay_prob=float(get("inbound_delay_prob", default_cfg.inbound_delay_prob)),
        inbound_delay_mean_steps=float(
            get("inbound_delay_mean_steps", default_cfg.inbound_delay_mean_steps)
        ),
        gdp_enabled=bool(get("gdp_enabled", default_cfg.gdp_enabled)),
        gdp_capacity_threshold=float(
            get("gdp_capacity_threshold", default_cfg.gdp_capacity_threshold)
        ),
        irops_enabled=bool(get("irops_enabled", default_cfg.irops_enabled)),
        irops_cancel_delay_threshold_steps=int(
            get(
                "irops_cancel_delay_threshold_steps",
                default_cfg.irops_cancel_delay_threshold_steps,
            )
        ),
        irops_max_cancels_per_step=int(
            get("irops_max_cancels_per_step", default_cfg.irops_max_cancels_per_step)
        ),
        seed=seed_val,
        shock_at_step=shock_at,
        shock_duration=shock_duration,
    )


def run_simulation(config: SimulationConfig) -> pd.DataFrame:
    """Run one simulation and return the time-series DataFrame."""
    model = AirportABM(config)
    model.run_model()
    return model.get_time_series()


def parse_args():
    p = argparse.ArgumentParser(
        description="Run Airport Resilience ABM for each row of an input CSV; write time-series and summary CSVs."
    )
    p.add_argument(
        "input_csv",
        type=str,
        nargs="?",
        default="config/batch_input.csv",
        help="Path to input CSV: one row per scenario (default: config/batch_input.csv)",
    )
    p.add_argument(
        "--time-series-csv",
        type=str,
        default="output/batch_time_series.csv",
        help="Output path for time-series data (default: output/batch_time_series.csv)",
    )
    p.add_argument(
        "--summary-csv",
        type=str,
        default="output/batch_summary.csv",
        help="Output path for summary metrics (default: output/batch_summary.csv)",
    )
    p.add_argument(
        "--runs-per-scenario",
        type=int,
        default=1,
        help="Number of runs per scenario (different seeds: seed_base, seed_base+1, ...). Default 1.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    from config.defaults import build_simulation_config

    default_model = get_default_config()
    default_cfg = build_simulation_config(
        default_model,
        shock_at_step=60,
        shock_duration=12,
        seed=42,
    )

    input_path = Path(args.input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    scenarios = pd.read_csv(input_path)
    if len(scenarios) == 0:
        raise ValueError("Input CSV has no rows.")

    # Optional scenario_id column
    if "scenario_id" not in scenarios.columns:
        scenarios["scenario_id"] = range(len(scenarios))

    all_ts = []
    summary_rows = []

    for idx, row in scenarios.iterrows():
        scenario_id = row["scenario_id"]
        config = row_to_config(row, default_cfg)
        seed_base = int(row.get("seed_base", 42))
        runs_per = args.runs_per_scenario

        for run in range(runs_per):
            run_config = copy_simulation_config(config, seed=seed_base + run)
            df = run_simulation(run_config)
            df["scenario_id"] = scenario_id
            df["run"] = run
            all_ts.append(df)

            shock_at = config.shock_at_step
            shock_end = (
                (shock_at + config.shock_duration - 1)
                if shock_at is not None
                else None
            )
            metrics = compute_resilience_metrics(
                df,
                shock_start_step=shock_at,
                shock_end_step=shock_end,
            )
            # One row for sensitivity/uncertainty: inputs + outputs
            summary = {
                "scenario_id": scenario_id,
                "run": run,
                "n_steps": config.n_steps,
                "flights_per_step": config.flights_per_step,
                "n_gates": config.n_gates,
                "n_airlines": config.n_airlines,
                "runway_slots_per_step": config.runway_slots_per_step,
                "terminal_capacity": config.terminal_capacity,
                "shock_at_step": shock_at if shock_at is not None else "",
                "shock_duration": config.shock_duration,
                "seed": seed_base + run,
            }
            summary["gates_per_airline"] = ",".join(map(str, config.gates_per_airline)) if config.gates_per_airline else ""
            summary["airline_flight_share"] = ",".join(map(str, config.airline_flight_share)) if config.airline_flight_share else ""
            summary.update(metrics)
            summary_rows.append(summary)

    ts_df = pd.concat(all_ts, ignore_index=True)
    summary_df = pd.DataFrame(summary_rows)

    out_ts = Path(args.time_series_csv)
    out_ts.parent.mkdir(parents=True, exist_ok=True)
    export_time_series(ts_df, out_ts)
    print(f"Time series written to {out_ts} ({len(ts_df)} rows)")

    out_summary = Path(args.summary_csv)
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    export_metrics(summary_df, out_summary)
    print(f"Summary (sensitivity/uncertainty) written to {out_summary} ({len(summary_df)} rows)")


if __name__ == "__main__":
    main()
