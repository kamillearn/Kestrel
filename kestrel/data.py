"""CSV loader -> Local-indexed bars."""
from __future__ import annotations
import pandas as pd

def load_csv(path, target_tz="America/New_York", source_tz="UTC"):
    df = pd.read_csv(path)
    if "spread" not in df.columns: df["spread"] = 0.0

    # Ensure all timestamps start as true UTC
    t = pd.to_datetime(df["time"], utc=True)

    # Convert to the TARGET market's local timezone (absorbs all DST shifts)
    t_local = t.dt.tz_convert(target_tz)

    # Hijack the "etdate" and "et_min" columns so backtester.py continues to work,
    # but mathematically, these are now LOCAL dates and LOCAL minutes!
    df["etdate"] = t_local.dt.strftime("%Y-%m-%d")
    df["et_min"] = t_local.dt.hour * 60 + t_local.dt.minute

    return df