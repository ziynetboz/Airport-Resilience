"""
Graphs and visualization for time series and resilience metrics.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use("Agg")
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False


def _require_mpl():
    if not _HAS_MPL:
        raise ImportError(
            "Plotting requires matplotlib. Install with: pip install matplotlib"
        )


def plot_time_series(
    df: pd.DataFrame,
    path: Optional[str | Path] = None,
    *,
    run: Optional[int] = None,
    shock_start: Optional[int] = None,
    shock_end: Optional[int] = None,
    figsize: tuple[float, float] = (12, 10),
) -> "plt.Figure":
    """
    Plot main time-series variables: throughput, queues, weather, travelers.

    Args:
        df: Time-series DataFrame (step, flights_completed, arrival_queue, etc.).
        path: If set, save figure to this path.
        run: If df has a 'run' column, plot only this run.
        shock_start, shock_end: If set, shade the shock interval.
        figsize: Figure size (width, height).

    Returns:
        matplotlib Figure.
    """
    _require_mpl()
    if run is not None and "run" in df.columns:
        df = df[df["run"] == run].copy()
    df = df.sort_values("step").reset_index(drop=True)
    if df.empty:
        raise ValueError("No data to plot")

    fig, axes = plt.subplots(2, 2, figsize=figsize, sharex=True)
    steps = df["step"].values

    def shade_shock(ax):
        if shock_start is not None and shock_end is not None:
            ax.axvspan(shock_start, shock_end, alpha=0.2, color="gray", label="Shock")

    # Throughput and cancellations
    ax = axes[0, 0]
    if "flights_completed" in df.columns:
        ax.plot(steps, df["flights_completed"], label="Flights completed", color="C0")
    if "flights_cancelled" in df.columns:
        ax.plot(steps, df["flights_cancelled"], label="Flights cancelled", color="C1")
    ax.set_ylabel("Flights (per step)")
    ax.set_title("Throughput per step")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    shade_shock(ax)

    # Queues
    ax = axes[0, 1]
    if "arrival_queue" in df.columns:
        ax.plot(steps, df["arrival_queue"], label="Arrival queue", color="C0")
    if "departure_queue" in df.columns:
        ax.plot(steps, df["departure_queue"], label="Departure queue", color="C1")
    ax.set_ylabel("Queue length (flights)")
    ax.set_title("Runway queues")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    shade_shock(ax)

    # Weather
    ax = axes[1, 0]
    if "weather_shock" in df.columns:
        ax.fill_between(steps, 0, df["weather_shock"], alpha=0.7, color="C2", label="Shock")
    if "weather_capacity_factor" in df.columns:
        ax.plot(steps, df["weather_capacity_factor"], label="Capacity factor", color="C3")
    ax.set_ylabel("Capacity factor (dimensionless)")
    ax.set_title("Weather shock & capacity factor")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    shade_shock(ax)

    # Travelers
    ax = axes[1, 1]
    if "travelers_in_terminal" in df.columns:
        ax.plot(steps, df["travelers_in_terminal"], label="In terminal", color="C0")
    if "travelers_stranded" in df.columns:
        ax.plot(steps, df["travelers_stranded"], label="Stranded", color="C1")
    ax.set_ylabel("Count (travelers)")
    ax.set_title("Travelers")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    shade_shock(ax)

    for ax in axes[1, :]:
        ax.set_xlabel("Step")
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches="tight")
    return fig


def plot_metrics_summary(
    metrics_df: pd.DataFrame,
    path: Optional[str | Path] = None,
    *,
    figsize: tuple[float, float] = (10, 6),
) -> "plt.Figure":
    """
    Plot resilience metrics across runs (e.g. bar or box for key metrics).

    Args:
        metrics_df: DataFrame with columns like baseline_throughput,
            during_shock_throughput, recovery_time_steps, etc.
        path: If set, save figure to this path.
        figsize: Figure size.

    Returns:
        matplotlib Figure.
    """
    _require_mpl()
    if metrics_df.empty:
        raise ValueError("No metrics to plot")

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Throughput: baseline vs during shock
    ax = axes[0]
    cols = ["baseline_throughput", "during_shock_throughput"]
    present = [c for c in cols if c in metrics_df.columns]
    if present:
        metrics_df[present].plot(kind="bar", ax=ax, width=0.7)
        ax.set_xticklabels(metrics_df["run"] if "run" in metrics_df.columns else range(len(metrics_df)))
        ax.set_ylabel("Throughput (flights/step)")
        ax.set_xlabel("Run")
        ax.set_title("Baseline vs during-shock throughput")
        ax.legend(title="")
    ax.grid(True, alpha=0.3)

    # Recovery time (steps)
    ax = axes[1]
    if "recovery_time_steps" in metrics_df.columns:
        metrics_df["recovery_time_steps"].plot(kind="bar", ax=ax, color="C0", width=0.7)
        ax.set_xticklabels(metrics_df["run"] if "run" in metrics_df.columns else range(len(metrics_df)))
        ax.set_ylabel("Recovery time (steps)")
        ax.set_xlabel("Run")
        ax.set_title("Recovery time (steps to ≥90% baseline)")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches="tight")
    return fig


def plot_run_summary(
    ts_df: pd.DataFrame,
    metrics_df: Optional[pd.DataFrame] = None,
    path: Optional[str | Path] = None,
    *,
    run: Optional[int] = None,
    shock_start: Optional[int] = None,
    shock_end: Optional[int] = None,
    figsize: tuple[float, float] = (14, 12),
) -> "plt.Figure":
    """
    Single figure with time-series panels and optional metrics summary.

    Args:
        ts_df: Time-series DataFrame.
        metrics_df: Optional resilience metrics (one row per run).
        path: If set, save figure to this path.
        run: If ts_df has 'run', use this run for time series.
        shock_start, shock_end: Shade shock interval in time-series panels.
        figsize: Figure size.

    Returns:
        matplotlib Figure.
    """
    _require_mpl()
    nrows = 2 if metrics_df is None or metrics_df.empty else 3
    fig, axes = plt.subplots(nrows, 2, figsize=figsize, sharex=False, constrained_layout=True)

    if run is not None and "run" in ts_df.columns:
        plot_df = ts_df[ts_df["run"] == run].sort_values("step")
    else:
        plot_df = ts_df.sort_values("step")
    steps = plot_df["step"].values

    def shade(ax):
        if shock_start is not None and shock_end is not None:
            ax.axvspan(shock_start, shock_end, alpha=0.2, color="gray")

    # Row 0: throughput, queues
    ax = axes[0, 0]
    if "flights_completed" in plot_df.columns:
        ax.plot(steps, plot_df["flights_completed"], color="C0", label="Completed")
    if "flights_cancelled" in plot_df.columns:
        ax.plot(steps, plot_df["flights_cancelled"], color="C1", label="Cancelled")
    ax.set_ylabel("Flights (per step)")
    ax.set_title("Throughput")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    shade(ax)

    ax = axes[0, 1]
    if "arrival_queue" in plot_df.columns:
        ax.plot(steps, plot_df["arrival_queue"], color="C0", label="Arrival")
    if "departure_queue" in plot_df.columns:
        ax.plot(steps, plot_df["departure_queue"], color="C1", label="Departure")
    ax.set_ylabel("Queue length (flights)")
    ax.set_title("Queues")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    shade(ax)

    # Row 1: weather, travelers
    ax = axes[1, 0]
    if "weather_capacity_factor" in plot_df.columns:
        ax.plot(steps, plot_df["weather_capacity_factor"], color="C2")
    if "weather_shock" in plot_df.columns:
        ax.fill_between(steps, 0, plot_df["weather_shock"], alpha=0.5, color="C3")
    ax.set_ylabel("Capacity factor (dimensionless)")
    ax.set_title("Weather (capacity factor & shock)")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    shade(ax)

    ax = axes[1, 1]
    if "travelers_in_terminal" in plot_df.columns:
        ax.plot(steps, plot_df["travelers_in_terminal"], color="C0", label="In terminal")
    if "travelers_stranded" in plot_df.columns:
        ax.plot(steps, plot_df["travelers_stranded"], color="C1", label="Stranded")
    ax.set_ylabel("Count (travelers)")
    ax.set_title("Travelers")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    shade(ax)

    if nrows == 3 and metrics_df is not None and not metrics_df.empty:
        ax = axes[2, 0]
        if "baseline_throughput" in metrics_df.columns and "during_shock_throughput" in metrics_df.columns:
            metrics_df[["baseline_throughput", "during_shock_throughput"]].plot(kind="bar", ax=ax)
            ax.set_xticklabels(metrics_df.get("run", range(len(metrics_df))))
            ax.set_ylabel("Throughput (flights/step)")
            ax.set_xlabel("Run")
            ax.set_title("Throughput by run")
        ax = axes[2, 1]
        if "recovery_time_steps" in metrics_df.columns:
            metrics_df["recovery_time_steps"].plot(kind="bar", ax=ax, color="C0")
            ax.set_xticklabels(metrics_df.get("run", range(len(metrics_df))))
            ax.set_ylabel("Recovery time (steps)")
            ax.set_xlabel("Run")
            ax.set_title("Recovery time (steps)")

    for ax in axes[1, :]:
        ax.set_xlabel("Step")
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches="tight")
    return fig


def plot_resilience_curve(
    df: pd.DataFrame,
    path: Optional[str | Path] = None,
    *,
    run: Optional[int] = None,
    shock_start: Optional[int] = None,
    shock_end: Optional[int] = None,
    recovery_threshold: float = 0.9,
    figsize: tuple[float, float] = (10, 6),
) -> "plt.Figure":
    """
    Plot the resilience curve: normalized throughput over time.
    Shows baseline (1.0), drop during shock, and recovery trajectory.
    Key KPI for airport resilience.

    Args:
        df: Time-series DataFrame with step, flights_completed.
        path: If set, save figure to this path.
        run: If df has 'run', plot only this run.
        shock_start, shock_end: Shade shock interval; baseline from pre-shock.
        recovery_threshold: Fraction of baseline for recovery (default 0.9).
        figsize: Figure size.

    Returns:
        matplotlib Figure.
    """
    _require_mpl()
    if run is not None and "run" in df.columns:
        df = df[df["run"] == run].copy()
    df = df.sort_values("step").reset_index(drop=True)
    if df.empty or "flights_completed" not in df.columns:
        raise ValueError("No data or flights_completed column")

    steps = df["step"].values
    throughput = df["flights_completed"].values

    if shock_start is not None:
        pre = df[df["step"] < shock_start]
        baseline = float(pre["flights_completed"].mean()) if len(pre) > 0 else 1.0
    else:
        baseline = float(df["flights_completed"].mean()) if len(df) > 0 else 1.0

    if baseline <= 0:
        baseline = 1.0
    normalized = throughput / baseline

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(steps, normalized, color="C0", linewidth=2, label="Throughput / baseline")
    ax.axhline(1.0, color="green", linestyle="--", alpha=0.7, label="Baseline (100%)")
    ax.axhline(recovery_threshold, color="orange", linestyle="--", alpha=0.7,
                label=f"Recovery threshold ({recovery_threshold*100:.0f}%)")

    if shock_start is not None and shock_end is not None:
        ax.axvspan(shock_start, shock_end, alpha=0.2, color="red", label="Shock")
    ax.set_xlabel("Step")
    ax.set_ylabel("Normalized throughput (dimensionless)")
    ax.set_title("Resilience curve: throughput relative to baseline")
    ax.set_ylim(-0.05, 1.15)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches="tight")
    return fig


def plot_kpis(
    df: pd.DataFrame,
    path: Optional[str | Path] = None,
    *,
    run: Optional[int] = None,
    shock_start: Optional[int] = None,
    shock_end: Optional[int] = None,
    figsize: tuple[float, float] = (12, 10),
) -> "plt.Figure":
    """
    Plot key airport resilience KPIs: resilience curve, gate utilization,
    total queue, stranded travelers, plus Horton critical-function KPIs
    (throughput efficiency, queue imbalance, stranding proportion, traveler exit rate).

    Args:
        df: Time-series DataFrame.
        path: If set, save figure to this path.
        run: If df has 'run', plot only this run.
        shock_start, shock_end: Shade shock interval.
        figsize: Figure size.

    Returns:
        matplotlib Figure.
    """
    _require_mpl()
    if run is not None and "run" in df.columns:
        df = df[df["run"] == run].copy()
    df = df.sort_values("step").reset_index(drop=True)
    if df.empty:
        raise ValueError("No data to plot")

    steps = df["step"].values

    def shade(ax):
        if shock_start is not None and shock_end is not None:
            ax.axvspan(shock_start, shock_end, alpha=0.2, color="gray")

    fig, axes = plt.subplots(4, 2, figsize=(figsize[0], figsize[1] * 1.8), sharex=True)

    # 1. Resilience curve (normalized throughput)
    ax = axes[0, 0]
    if "flights_completed" in df.columns:
        pre = df[df["step"] < shock_start] if shock_start is not None else df
        baseline = float(pre["flights_completed"].mean()) if len(pre) > 0 else 1.0
        if baseline <= 0:
            baseline = 1.0
        ax.plot(steps, df["flights_completed"] / baseline, color="C0", linewidth=2)
        ax.axhline(1.0, color="green", linestyle="--", alpha=0.6)
        ax.axhline(0.9, color="orange", linestyle="--", alpha=0.6)
    ax.set_ylabel("Normalized throughput (dimensionless)")
    ax.set_title("Resilience curve (throughput / baseline)")
    ax.set_ylim(-0.05, 1.15)
    ax.grid(True, alpha=0.3)
    shade(ax)

    # 2. Gate utilization
    ax = axes[0, 1]
    if "gate_utilization" in df.columns:
        ax.plot(steps, df["gate_utilization"] * 100, color="C1", linewidth=2)
        ax.set_ylabel("Gate utilization (%)")
        ax.set_ylim(-5, 105)
    elif "gates_available" in df.columns:
        ax.plot(steps, df["gates_available"], color="C1", label="Gates available")
        ax.set_ylabel("Gates available (count)")
    ax.set_title("Gate utilization")
    ax.grid(True, alpha=0.3)
    shade(ax)

    # 3. Total queue (arrival + departure)
    ax = axes[1, 0]
    if "total_queue" in df.columns:
        ax.plot(steps, df["total_queue"], color="C2", linewidth=2)
    elif "arrival_queue" in df.columns and "departure_queue" in df.columns:
        ax.plot(steps, df["arrival_queue"] + df["departure_queue"], color="C2", linewidth=2)
    ax.set_ylabel("Queue length (flights)")
    ax.set_title("Total runway queue (arrival + departure)")
    ax.grid(True, alpha=0.3)
    shade(ax)

    # 4. Stranded travelers
    ax = axes[1, 1]
    if "travelers_stranded" in df.columns:
        ax.plot(steps, df["travelers_stranded"], color="C3", linewidth=2, label="Stranded")
    if "travelers_in_terminal" in df.columns:
        ax.plot(steps, df["travelers_in_terminal"], color="C0", alpha=0.7, label="In terminal")
    ax.set_ylabel("Count (travelers)")
    ax.set_title("Travelers (stranded vs in terminal)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    shade(ax)

    # 5. Throughput efficiency (cf1: airfield efficiency)
    ax = axes[2, 0]
    if "flights_completed" in df.columns and "effective_slots" in df.columns:
        eff = df["flights_completed"] / df["effective_slots"].replace(0, 1)
        ax.plot(steps, eff, color="C4", linewidth=2)
        ax.axhline(1.0, color="green", linestyle="--", alpha=0.6)
    ax.set_ylabel("Throughput / capacity (dimensionless)")
    ax.set_title("Throughput efficiency (cf1: landings/takeoffs)")
    ax.set_ylim(-0.05, 1.15)
    ax.grid(True, alpha=0.3)
    shade(ax)

    # 6. Queue imbalance (cf1/cf4: coordination)
    ax = axes[2, 1]
    if "arrival_queue" in df.columns and "departure_queue" in df.columns:
        imb = (df["arrival_queue"] - df["departure_queue"]).abs()
        ax.plot(steps, imb, color="C5", linewidth=2)
    ax.set_ylabel("|Arrival − Departure| (flights)")
    ax.set_title("Queue imbalance (cf1/cf4: coordination)")
    ax.grid(True, alpha=0.3)
    shade(ax)

    # 7. Stranding proportion (cf2: passenger safety)
    ax = axes[3, 0]
    if "travelers_stranded" in df.columns and "travelers_in_terminal" in df.columns:
        prop = df["travelers_stranded"] / df["travelers_in_terminal"].replace(0, 1)
        ax.plot(steps, prop * 100, color="C6", linewidth=2)
    ax.set_ylabel("Stranded / in terminal (%)")
    ax.set_title("Stranding proportion (cf2: passenger safety)")
    ax.set_ylim(-5, 105)
    ax.grid(True, alpha=0.3)
    shade(ax)

    # 8. Traveler exit rate (cf2: operational continuity)
    ax = axes[3, 1]
    if "travelers_exited_this_step" in df.columns:
        ax.plot(steps, df["travelers_exited_this_step"], color="C7", linewidth=2)
    ax.set_ylabel("Travelers exited (per step)")
    ax.set_title("Traveler exit rate (cf2: operational continuity)")
    ax.grid(True, alpha=0.3)
    shade(ax)

    for ax in axes[3, :]:
        ax.set_xlabel("Step")
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches="tight")
    return fig
