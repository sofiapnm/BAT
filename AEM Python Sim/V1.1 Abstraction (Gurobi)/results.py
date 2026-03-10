import pandas as pd

from parameters.battery import BATTERY_ECONOMIC
from parameters.grid_import import IMPORT_EMISSIONS
from parameters.grid_export import EXPORT_EMISSIONS


def extract_solution(vars_dict, n):
    return pd.DataFrame(
        {
            "grid_import_kWh": [vars_dict["grid_import"][t].X for t in range(n)],
            "grid_export_kWh": [vars_dict["grid_export"][t].X for t in range(n)],
            "battery_charge_kWh": [vars_dict["batt_charge"][t].X for t in range(n)],
            "battery_discharge_kWh": [vars_dict["batt_discharge"][t].X for t in range(n)],
            "battery_soc_kWh": [vars_dict["soc"][t].X for t in range(n)],
        }
    )


def build_kwh_results_table(datetime_series, load_profile, production_profile, solution):
    results = pd.DataFrame({"DateTime": datetime_series})
    results["load_kWh"] = pd.Series(load_profile, index=results.index, dtype=float)
    results["production_kWh"] = pd.Series(production_profile, index=results.index, dtype=float)

    for col in solution.columns:
        results[col] = solution[col].values

    return results


def build_results_table(datetime_series, sol_cost, sol_emis, spot_price):
    results = pd.DataFrame({"DateTime": datetime_series})

    for col in sol_cost.columns:
        results[f"cost_opt__{col}"] = sol_cost[col].values

    for col in sol_emis.columns:
        results[f"emissions_opt__{col}"] = sol_emis[col].values

    throughput_cost = BATTERY_ECONOMIC["throughput_cost_rp_per_kwh"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_credit = EXPORT_EMISSIONS["export_emissions_credit_kgco2_per_kwh"]

    spot_price_series = pd.Series(spot_price, index=results.index, dtype=float)

    results["cost_opt__step_cost_rp"] = (
        results["cost_opt__grid_import_kWh"] * spot_price_series
        - results["cost_opt__grid_export_kWh"] * spot_price_series
        + throughput_cost
        * (
            results["cost_opt__battery_charge_kWh"]
            + results["cost_opt__battery_discharge_kWh"]
        )
    )

    results["emissions_opt__step_cost_rp"] = (
        results["emissions_opt__grid_import_kWh"] * spot_price_series
        - results["emissions_opt__grid_export_kWh"] * spot_price_series
        + throughput_cost
        * (
            results["emissions_opt__battery_charge_kWh"]
            + results["emissions_opt__battery_discharge_kWh"]
        )
    )

    results["cost_opt__step_emissions_kgco2"] = (
        results["cost_opt__grid_import_kWh"] * grid_emissions
        - results["cost_opt__grid_export_kWh"] * export_credit
    )

    results["emissions_opt__step_emissions_kgco2"] = (
        results["emissions_opt__grid_import_kWh"] * grid_emissions
        - results["emissions_opt__grid_export_kWh"] * export_credit
    )

    return results


def save_results(results, output_path):
    results.to_csv(output_path, index=False)


def print_summary(results, output_path):
    total_cost_costobj = results["cost_opt__step_cost_rp"].sum()
    total_cost_emisobj = results["emissions_opt__step_cost_rp"].sum()
    total_emis_costobj = results["cost_opt__step_emissions_kgco2"].sum()
    total_emis_emisobj = results["emissions_opt__step_emissions_kgco2"].sum()

    print("Optimization complete.")
    print(f"Rows solved (15-min intervals): {len(results)}")
    print(f"Output file: {output_path}")
    print("")
    print("Annual totals")
    print(f"Cost objective -> total cost [Rp]: {total_cost_costobj:,.2f}")
    print(f"Cost objective -> total emissions [kgCO2]: {total_emis_costobj:,.2f}")
    print(f"Emissions objective -> total cost [Rp]: {total_cost_emisobj:,.2f}")
    print(f"Emissions objective -> total emissions [kgCO2]: {total_emis_emisobj:,.2f}")
