import pandas as pd


def load_input_data(data_path):
    df = pd.read_csv(data_path)
    df["DateTime"] = pd.to_datetime(df["DateTime"])
    df = df.sort_values("DateTime").reset_index(drop=True)

    numeric_cols = [
        "Total Production Hydro",
        "Sales",
        "District heating sales",
        "Spot price [Rp/kWh]",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df[numeric_cols] = df[numeric_cols].interpolate(limit_direction="both")
    df[numeric_cols] = df[numeric_cols].ffill().bfill()

    if df[numeric_cols].isna().any().any():
        raise ValueError("Input data still contains NaN in required numeric columns after cleaning.")

    elecdemand_kwhel = df["Sales"].to_numpy(dtype=float)
    heatdemand_kwhth = df["District heating sales"].to_numpy(dtype=float)

    return {
        "datetime": df["DateTime"].copy(),
        "production": df["Total Production Hydro"].to_numpy(dtype=float),
        "elecdemand_kwhel": elecdemand_kwhel,
        "heatdemand_kwhth": heatdemand_kwhth,
        # Backward-compatible aliases used by existing model code.
        "demand": elecdemand_kwhel,
        "elecdemand": elecdemand_kwhel,
        "heatdemand": heatdemand_kwhth,
        "spot_price": df["Spot price [Rp/kWh]"].to_numpy(dtype=float),
    }