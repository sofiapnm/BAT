from data_loader import load_input_data
import pandas as pd
import numpy as np
import sys
from model_builder import build_model, solve_model
from parameters.battery import BATTERY_TECHNICAL
from parameters.general import GENERAL
from results import (
    build_kwh_results_table,
    build_results_table,
    extract_monthly_peak_solution,
    extract_solution,
    print_summary,
    save_results,
)


# Set optimization horizon end month directly here (1-12), or None for full year.
OPTIMIZATION_END_MONTH = None


def _resolve_objective_mode():
    mode_from_general = GENERAL.get("optimization_mode")
    mode_from_argv = sys.argv[1] if len(sys.argv) > 1 else None

    mode_raw = mode_from_general if mode_from_general is not None else mode_from_argv
    if mode_raw is None:
        mode_raw = input("Choose optimization mode ('profit' or 'emission'): ")

    mode = str(mode_raw).strip().lower()
    mapping = {
        "profit": "cost",
        "cost": "cost",
        "emission": "emissions",
        "emissions": "emissions",
    }
    resolved = mapping.get(mode)
    if resolved is None:
        raise ValueError(
            f"Invalid optimization mode '{mode_raw}'. Use 'profit' or 'emission'."
        )
    return resolved

def main():
    data = load_input_data(GENERAL["data_path"])
    objective_mode = _resolve_objective_mode()

    print(f"Starting optimization run in '{objective_mode}' mode...")

    # Optional: limit optimization horizon Jan..END_MONTH (set directly in this file)
    end_month = OPTIMIZATION_END_MONTH
    if end_month is not None:
        # Integer-only configuration by design.
        if isinstance(end_month, int):
            end_month_num = end_month
        else:
            raise ValueError(
                f"Invalid OPTIMIZATION_END_MONTH: {end_month}. Use integer 1..12 or None."
            )
        if end_month_num is None or not (1 <= end_month_num <= 12):
            raise ValueError(
                f"Invalid OPTIMIZATION_END_MONTH: {end_month}. Use integer 1..12 or None."
            )

        dt = pd.to_datetime(data["datetime"])
        start_year = int(dt.iloc[0].year)
        mask = (dt.dt.year == start_year) & (dt.dt.month <= end_month_num) & (dt.dt.month >= 1)
        mask_array = mask.to_numpy() if isinstance(mask, pd.Series) else mask

        # Apply mask to each timeseries in data (support Series, ndarray, list)
        data = {
            k: (
                v[mask_array] if isinstance(v, pd.Series)
                else np.asarray(v)[mask_array]
            )
            for k, v in data.items()
        }

        print(f"Optimizing Jan..{end_month_num} of {start_year} (timesteps: {len(data['production'])})")
    else:
        print(f"Optimizing full horizon (timesteps: {len(data['production'])})")

    full_horizon_init_soc = (
        BATTERY_TECHNICAL["soc_init_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
    )
    full_horizon_end_soc = (
        BATTERY_TECHNICAL["soc_end_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
    )

    model, vars_dict = build_model(
        production_kwh=data["production"],
        elecdemand_kwh=data["elecdemand_kwhel"],
        heatdemand_kwhth=data["heatdemand_kwhth"],
        spot_price_rp_per_kwh=data["spot_price"],
        datetime_series=data["datetime"],
        objective_mode=objective_mode,
        init_soc_kwh=full_horizon_init_soc,
        final_soc_kwh=full_horizon_end_soc,
    )
    print(f"Solving {objective_mode} model...")
    solve_model(model, objective_mode=objective_mode)
    print(f"{objective_mode.capitalize()} model solved.")

    selected_solution = extract_solution(vars_dict, len(data["demand"]))
    selected_monthly_peak = extract_monthly_peak_solution(vars_dict)

    if objective_mode == "cost":
        sol_cost = selected_solution
        monthly_peak_cost = selected_monthly_peak
        sol_emis = selected_solution.copy()
        monthly_peak_emis = selected_monthly_peak.copy()
    else:
        sol_emis = selected_solution
        monthly_peak_emis = selected_monthly_peak
        sol_cost = selected_solution.copy()
        monthly_peak_cost = selected_monthly_peak.copy()

    kwh_results = build_kwh_results_table(
        datetime_series=data["datetime"],
        load_profile=data["elecdemand_kwhel"],
        heatdemand_profile=data["heatdemand_kwhth"],
        production_profile=data["production"],
        spot_price_profile=data["spot_price"],
        solution=selected_solution,
    )

    results = build_results_table(
        datetime_series=data["datetime"],
        sol_cost=sol_cost,
        sol_emis=sol_emis,
        production=data["production"],
        heatdemand_profile=data["heatdemand_kwhth"],
        spot_price=data["spot_price"],
        monthly_peak_cost=monthly_peak_cost,
        monthly_peak_emis=monthly_peak_emis,
    )

    save_results(kwh_results, GENERAL["kwh_output_path"])
    save_results(results, GENERAL["output_path"])
    print_summary(results, GENERAL["output_path"])
    print("Done.")


if __name__ == "__main__":
    main()
