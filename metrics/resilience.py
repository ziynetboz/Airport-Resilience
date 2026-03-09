"""
Resilience metrics: throughput, recovery time, queues, stranding.
"""

from typing import Optional

import pandas as pd


def compute_resilience_metrics(
    df: pd.DataFrame,
    shock_start_step: Optional[int] = None,
    shock_end_step: Optional[int] = None,
    recovery_threshold: float = 0.9,
) -> dict:
    """
    Compute resilience metrics from a model run DataFrame.

    df: columns step, flights_completed, arrival_queue, departure_queue,
        weather_shock, travelers_in_terminal, flights_cancelled, etc.
    shock_start_step, shock_end_step: if provided, baseline is pre-shock.
    recovery_threshold: fraction of baseline throughput to count as recovered.
    """
    df = df.copy()
    if "step" not in df.columns and getattr(df.index, "name", None) == "Step":
        df = df.reset_index().rename(columns={"Step": "step"})
    elif "step" not in df.columns and len(df) > 0:
        df["step"] = range(len(df))
    metrics: dict = {}

    if "flights_completed" in df.columns:
        metrics["total_flights_completed"] = df["flights_completed"].sum()
        metrics["mean_throughput_per_step"] = float(df["flights_completed"].mean())
        metrics["max_throughput_step"] = int(df["flights_completed"].max())

    if "flights_cancelled" in df.columns:
        metrics["total_flights_cancelled"] = int(df["flights_cancelled"].sum())

    if shock_start_step is not None and shock_end_step is not None:
        pre = df[df["step"] < shock_start_step]
        during = df[
            (df["step"] >= shock_start_step) & (df["step"] <= shock_end_step)
        ]
        post = df[df["step"] > shock_end_step]
        if len(pre) > 0 and "flights_completed" in df.columns:
            baseline_throughput = float(pre["flights_completed"].mean())
            metrics["baseline_throughput"] = baseline_throughput
            if len(during) > 0:
                metrics["during_shock_throughput"] = float(
                    during["flights_completed"].mean()
                )
                metrics["throughput_drop_ratio"] = (
                    1
                    - metrics["during_shock_throughput"] / baseline_throughput
                    if baseline_throughput > 0
                    else 0
                )
            if len(post) > 0 and baseline_throughput > 0:
                target = recovery_threshold * baseline_throughput
                post_sorted = post.sort_values("step")
                recovery_step = None
                for _, row in post_sorted.iterrows():
                    if row["flights_completed"] >= target:
                        recovery_step = int(row["step"])
                        break
                metrics["recovery_step"] = recovery_step
                metrics["recovery_time_steps"] = (
                    recovery_step - shock_end_step if recovery_step else None
                )

        if "arrival_queue" in df.columns and "departure_queue" in df.columns:
            if len(during) > 0:
                metrics["max_arrival_queue_during_shock"] = int(
                    during["arrival_queue"].max()
                )
                metrics["max_departure_queue_during_shock"] = int(
                    during["departure_queue"].max()
                )

    if "travelers_in_terminal" in df.columns:
        metrics["max_travelers_in_terminal"] = int(
            df["travelers_in_terminal"].max()
        )
        metrics["mean_travelers_in_terminal"] = float(
            df["travelers_in_terminal"].mean()
        )

    if "travelers_stranded" in df.columns and len(df) > 0:
        metrics["stranded"] = int(df["travelers_stranded"].iloc[-1])

    return metrics


def summarize_runs(
    run_dfs: list,
    shock_start_step: Optional[int] = None,
    shock_end_step: Optional[int] = None,
) -> pd.DataFrame:
    """
    run_dfs: list of (label, DataFrame) or list of DataFrames.
    Returns a summary DataFrame of resilience metrics across runs.
    """
    rows = []
    for i, item in enumerate(run_dfs):
        if isinstance(item, tuple):
            label, df = item
        else:
            label = f"run_{i}"
            df = item
        m = compute_resilience_metrics(
            df, shock_start_step, shock_end_step
        )
        m["run"] = label
        rows.append(m)
    return pd.DataFrame(rows)
