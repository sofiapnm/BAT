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

    # Optional: limit optimization horizon Jan..END_MONTH (set in parameters.general)
    end_month = GENERAL.get("optimization_end_month", None)
    if end_month is not None:
        # parse month (accept int 1-12 or name like 'June' or 'jun')
        if isinstance(end_month, int):
            end_month_num = int(end_month)
        else:
            name = str(end_month).strip().lower()
            months = {
                'january':1,'jan':1,'february':2,'feb':2,'march':3,'mar':3,
                'april':4,'apr':4,'may':5,'june':6,'jun':6,'july':7,'jul':7,
                'august':8,'aug':8,'september':9,'sep':9,'october':10,'oct':10,
                'november':11,'nov':11,'december':12,'dec':12
            }
            if name.isdigit():
                end_month_num = int(name)
            else:
                end_month_num = months.get(name, None)
        if end_month_num is None or not (1 <= end_month_num <= 12):
            raise ValueError(f"Invalid GENERAL['optimization_end_month']: {end_month}")

        dt = pd.to_datetime(data["datetime"])
        start_year = int(dt.iloc[0].year)
        mask = (dt.dt.year == start_year) & (dt.dt.month <= end_month_num) & (dt.dt.month >= 1)

        # Apply mask to each timeseries in data (support Series, ndarray, list)
        data = {
            k: (v[mask] if isinstance(v, pd.Series) else np.asarray(v)[mask.to_numpy()])
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
