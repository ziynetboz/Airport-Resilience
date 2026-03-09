"""
Data export: time series and resilience metrics to CSV and other formats.
"""

from pathlib import Path
from typing import Optional

import pandas as pd


def export_time_series(
    df: pd.DataFrame,
    path: str | Path,
    *,
    include_run: bool = True,
) -> Path:
    """
    Export time-series DataFrame to CSV.

    Args:
        df: DataFrame with columns step, flights_completed, queues, etc.
        path: Output file path (e.g. 'output/ts.csv').
        include_run: If True, keep a 'run' column if present.

    Returns:
        Resolved output path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if not include_run and "run" in out.columns:
        out = out.drop(columns=["run"])
    out.to_csv(path, index=False)
    return path.resolve()


def export_metrics(
    metrics_df: pd.DataFrame,
    path: str | Path,
) -> Path:
    """
    Export resilience metrics DataFrame to CSV.

    Args:
        metrics_df: DataFrame with one row per run and resilience metric columns.
        path: Output file path (e.g. 'output/resilience.csv').

    Returns:
        Resolved output path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(path, index=False)
    return path.resolve()
