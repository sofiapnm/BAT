from pathlib import Path

import pandas as pd

from model_builder import build_model, solve_model
from parameters.battery import BATTERY_TECHNICAL
from parameters.general import GENERAL
from parameters.grid_import import (
    annual_grid_use_hours as annual_import_grid_use_hours,
    power_tariff_rp_per_kw_per_month,
)
from results import (
    extract_monthly_peak_solution,
    extract_solution,
    save_results,
    summarize_solution,
)


def build_pareto_caps(min_emissions_kgco2, max_emissions_kgco2, num_points):
    if num_points <= 2 or max_emissions_kgco2 <= min_emissions_kgco2:
        return []

    step = (max_emissions_kgco2 - min_emissions_kgco2) / (num_points - 1)
    return [float(min_emissions_kgco2 + i * step) for i in range(1, num_points - 1)]


def reconstruct_solution(results, prefix):
    solution = pd.DataFrame(index=results.index)
    for column in results.columns:
        if column.startswith(prefix):
            solution[column.removeprefix(prefix)] = results[column].astype(float)
    return solution


def reconstruct_monthly_peak(results, solution_prefix):
    annual_import_kwh = float(results[f"{solution_prefix}grid_import_kWh"].sum())
    annual_export_kwh = float(results[f"{solution_prefix}grid_export_kWh"].sum())
    annual_grid_use_h = annual_import_grid_use_hours(annual_import_kwh, annual_export_kwh)
    power_tariff = power_tariff_rp_per_kw_per_month(annual_grid_use_h)

    month_labels = pd.to_datetime(results["DateTime"]).dt.to_period("M").astype(str)
    first_step_in_month = ~month_labels.duplicated()
    monthly_power_tariff = results.loc[
        first_step_in_month, f"{solution_prefix}monthly_power_tariff_rp"
    ].astype(float)
    monthly_peak = monthly_power_tariff / power_tariff
    monthly_peak.index = month_labels[first_step_in_month].values
    return monthly_peak.astype(float)


def load_anchor_summaries():
    kwh_path = Path(GENERAL["kwh_output_path"])
    output_path = Path(GENERAL["output_path"])
    if not kwh_path.exists() or not output_path.exists():
        raise FileNotFoundError(
            "Run main.py first so both annual result files are available."
        )

    kwh_results = pd.read_csv(kwh_path, parse_dates=["DateTime"])
    results = pd.read_csv(output_path, parse_dates=["DateTime"])

    cost_solution = kwh_results[
        [
            "battery_installed",
            "grid_import_kWh",
            "grid_export_kWh",
            "battery_charge_kWh",
            "battery_discharge_kWh",
            "battery_soc_kWh",
            "prod_for_local_demand_kWh",
            "woodchip_boiler_heat_kWhth",
            "woodchip_heat_supply_share",
        ]
    ].astype(float)
    emissions_solution = reconstruct_solution(results, "emissions_opt__")

    monthly_peak_cost = reconstruct_monthly_peak(results, "cost_opt__")
    monthly_peak_emis = reconstruct_monthly_peak(results, "emissions_opt__")

    cost_summary = summarize_solution(
        solution=cost_solution,
        production=kwh_results["production_kWh"],
        heatdemand=kwh_results["heatdemand_kWhth"],
        spot_price=kwh_results["spot price [Rp/kWh]"],
        monthly_peak=monthly_peak_cost,
    )
    emissions_summary = summarize_solution(
        solution=emissions_solution,
        production=kwh_results["production_kWh"],
        heatdemand=kwh_results["heatdemand_kWhth"],
        spot_price=kwh_results["spot price [Rp/kWh]"],
        monthly_peak=monthly_peak_emis,
    )

    return kwh_results, results, cost_summary, emissions_summary


def main():
    kwh_results, results, cost_summary, emissions_summary = load_anchor_summaries()

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

    full_horizon_init_soc = (
        BATTERY_TECHNICAL["soc_init_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
    )
    full_horizon_end_soc = (
        BATTERY_TECHNICAL["soc_end_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
    )

    production = kwh_results["production_kWh"]
    demand = kwh_results["load_kWh"]
    heatdemand = kwh_results["heatdemand_kWhth"]
    spot_price = kwh_results["spot price [Rp/kWh]"]
    datetime_series = kwh_results["DateTime"]

    for i, emissions_cap in enumerate(emissions_caps):
        model_pareto, vars_pareto = build_model(
            production_kwh=production,
            demand_kwh=demand,
            heatdemand_kwhth=heatdemand,
            spot_price_rp_per_kwh=spot_price,
            datetime_series=datetime_series,
            objective_mode="cost",
            init_soc_kwh=full_horizon_init_soc,
            final_soc_kwh=full_horizon_end_soc,
            emissions_cap_kgco2=emissions_cap,
        )
        solve_model(model_pareto, objective_mode=f"pareto_cost_cap_{i}")
        sol_pareto = extract_solution(vars_pareto, len(demand))
        monthly_peak_pareto = extract_monthly_peak_solution(vars_pareto)
        pareto_summary = summarize_solution(
            solution=sol_pareto,
            production=production,
            heatdemand=heatdemand,
            spot_price=spot_price,
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
        save_results(
            pd.DataFrame(pareto_rows).sort_values(by="annual_emissions_burden_kgco2"),
            GENERAL["pareto_output_path"],
        )
        print(
            f"Pareto progress: {i + 1}/{len(emissions_caps)} points saved to {GENERAL['pareto_output_path']}"
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
