import pandas as pd

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
    summarize_solution,
)


def build_pareto_caps(min_emissions_kgco2, max_emissions_kgco2, num_points):
    if num_points <= 2 or max_emissions_kgco2 <= min_emissions_kgco2:
        return []

    step = (max_emissions_kgco2 - min_emissions_kgco2) / (num_points - 1)
    return [float(min_emissions_kgco2 + i * step) for i in range(1, num_points - 1)]


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
        demand_kwh=data["demand"],
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
        demand_kwh=data["demand"],
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
        load_profile=data["demand"],
        production_profile=data["production"],
        spot_price_profile=data["spot_price"],
        solution=sol_cost,
    )

    results = build_results_table(
        datetime_series=data["datetime"],
        sol_cost=sol_cost,
        sol_emis=sol_emis,
        production=data["production"],
        spot_price=data["spot_price"],
        monthly_peak_cost=monthly_peak_cost,
        monthly_peak_emis=monthly_peak_emis,
    )

    save_results(kwh_results, GENERAL["kwh_output_path"])
    save_results(results, GENERAL["output_path"])
    print_summary(results, GENERAL["output_path"])

    cost_summary = summarize_solution(
        solution=sol_cost,
        production=data["production"],
        spot_price=data["spot_price"],
        monthly_peak=monthly_peak_cost,
    )
    emissions_summary = summarize_solution(
        solution=sol_emis,
        production=data["production"],
        spot_price=data["spot_price"],
        monthly_peak=monthly_peak_emis,
    )

    pareto_rows = [
        {
            "pareto_point": 0,
            "scenario": "emissions_anchor",
            "emissions_cap_kgco2": emissions_summary["annual_emissions_burden_kgco2"],
            **emissions_summary,
        }
    ]
    emissions_caps = build_pareto_caps(
        min_emissions_kgco2=emissions_summary["annual_emissions_burden_kgco2"],
        max_emissions_kgco2=cost_summary["annual_emissions_burden_kgco2"],
        num_points=GENERAL["pareto_num_points"],
    )

    for i, emissions_cap in enumerate(emissions_caps):
        model_pareto, vars_pareto = build_model(
            production_kwh=data["production"],
            demand_kwh=data["demand"],
            spot_price_rp_per_kwh=data["spot_price"],
            datetime_series=data["datetime"],
            objective_mode="cost",
            init_soc_kwh=full_horizon_init_soc,
            final_soc_kwh=full_horizon_end_soc,
            emissions_cap_kgco2=emissions_cap,
        )
        solve_model(model_pareto, objective_mode=f"pareto_cost_cap_{i}")
        sol_pareto = extract_solution(vars_pareto, len(data["demand"]))
        monthly_peak_pareto = extract_monthly_peak_solution(vars_pareto)
        pareto_summary = summarize_solution(
            solution=sol_pareto,
            production=data["production"],
            spot_price=data["spot_price"],
            monthly_peak=monthly_peak_pareto,
        )
        pareto_rows.append(
            {
                "pareto_point": i + 1,
                "scenario": "epsilon_constrained_cost",
                "emissions_cap_kgco2": emissions_cap,
                **pareto_summary,
            }
        )

    pareto_rows.append(
        {
            "pareto_point": len(pareto_rows),
            "scenario": "cost_anchor",
            "emissions_cap_kgco2": cost_summary["annual_emissions_burden_kgco2"],
            **cost_summary,
        }
    )

    pareto_results = pd.DataFrame(pareto_rows).sort_values(
        by="annual_emissions_burden_kgco2"
    )
    save_results(pareto_results, GENERAL["pareto_output_path"])
    print(f"Pareto front output file: {GENERAL['pareto_output_path']}")


if __name__ == "__main__":
    main()
