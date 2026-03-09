from typing import Tuple

import pandas as pd


REQUIRED_NUMERIC_COLUMNS = ["Total Production Hydro", "Sales", "Spot price [Rp/kWh]"]


def load_profiles(data_path: str) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """Load and clean fixed hydro/demand/price profiles."""
    df = pd.read_csv(data_path)
    df["DateTime"] = pd.to_datetime(df["DateTime"])
    df = df.sort_values("DateTime").reset_index(drop=True)

    for col in REQUIRED_NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df[REQUIRED_NUMERIC_COLUMNS] = df[REQUIRED_NUMERIC_COLUMNS].interpolate(limit_direction="both")
    df[REQUIRED_NUMERIC_COLUMNS] = df[REQUIRED_NUMERIC_COLUMNS].ffill().bfill()

    if df[REQUIRED_NUMERIC_COLUMNS].isna().any().any():
        raise ValueError("Input data still contains NaN in required numeric columns after cleaning.")

    production = df["Total Production Hydro"]
    demand = df["Sales"]
    spot_price = df["Spot price [Rp/kWh]"]
    return df, production, demand, spot_price
