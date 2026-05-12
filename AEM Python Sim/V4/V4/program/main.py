from data_loader import load_input_data
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

def main():
    data = load_input_data(GENERAL["data_path"])

    full_horizon_init_soc = (
        BATTERY_TECHNICAL["soc_init_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
    )
    full_horizon_end_soc = (
        BATTERY_TECHNICAL["soc_end_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
    )

    model_cost, vars_cost = build_model(
        production_kwh=data["production"],
        elecdemand_kwh=data["elecdemand_kwhel"],
        heatdemand_kwhth=data["heatdemand_kwhth"],
        spot_price_rp_per_kwh=data["spot_price"],
        datetime_series=data["datetime"],
        objective_mode="cost",
        init_soc_kwh=full_horizon_init_soc,
        final_soc_kwh=full_horizon_end_soc,
    )
    solve_model(model_cost, objective_mode="cost")
    sol_cost = extract_solution(vars_cost, len(data["demand"]))
    monthly_peak_cost = extract_monthly_peak_solution(vars_cost)

    model_emis, vars_emis = build_model(
        production_kwh=data["production"],
        elecdemand_kwh=data["elecdemand_kwhel"],
        heatdemand_kwhth=data["heatdemand_kwhth"],
        spot_price_rp_per_kwh=data["spot_price"],
        datetime_series=data["datetime"],
        objective_mode="emissions",
        init_soc_kwh=full_horizon_init_soc,
        final_soc_kwh=full_horizon_end_soc,
    )
    solve_model(model_emis, objective_mode="emissions")
    sol_emis = extract_solution(vars_emis, len(data["demand"]))
    monthly_peak_emis = extract_monthly_peak_solution(vars_emis)

    kwh_results = build_kwh_results_table(
        datetime_series=data["datetime"],
        load_profile=data["elecdemand_kwhel"],
        heatdemand_profile=data["heatdemand_kwhth"],
        production_profile=data["production"],
        spot_price_profile=data["spot_price"],
        solution=sol_cost,
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


if __name__ == "__main__":
    main()
