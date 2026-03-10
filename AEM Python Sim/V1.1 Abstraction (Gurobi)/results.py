import pandas as pd

from parameters.battery import BATTERY_ECONOMIC, BATTERY_TECHNICAL
from parameters.grid_import import IMPORT_ECONOMIC, IMPORT_EMISSIONS, import_price_rp_per_kwh
from parameters.grid_export import EXPORT_ECONOMIC, EXPORT_EMISSIONS, export_price_rp_per_kwh


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


def extract_monthly_peak_solution(vars_dict):
    monthly_peak = vars_dict["monthly_peak_kw"]
    unique_month_labels = vars_dict["unique_month_labels"]
    return pd.Series(
        {month_label: monthly_peak[month_label].X for month_label in unique_month_labels},
        dtype=float,
    )


def build_kwh_results_table(
    datetime_series,
    load_profile,
    production_profile,
    spot_price_profile,
    solution,
):
    results = pd.DataFrame({"DateTime": datetime_series})
    results["load_kWh"] = pd.Series(load_profile, index=results.index, dtype=float)
    results["production_kWh"] = pd.Series(production_profile, index=results.index, dtype=float)
    results["spot price [Rp/kWh]"] = pd.Series(
        spot_price_profile, index=results.index, dtype=float
    )

    for col in solution.columns:
        results[col] = solution[col].values

    return results


def build_results_table(datetime_series, sol_cost, sol_emis, spot_price, monthly_peak_cost, monthly_peak_emis):
    results = pd.DataFrame({"DateTime": datetime_series})

    for col in sol_cost.columns:
        results[f"cost_opt__{col}"] = sol_cost[col].values

    for col in sol_emis.columns:
        results[f"emissions_opt__{col}"] = sol_emis[col].values

    battery_capacity_kwh = BATTERY_TECHNICAL["capacity_kwh"]
    battery_capex = BATTERY_ECONOMIC["capex_rp"]
    battery_annual_opex = (
        BATTERY_ECONOMIC["annual_opex_rp_per_kwh_year"] * battery_capacity_kwh
    )
    battery_degradation_cost = BATTERY_ECONOMIC["degradation_cost_rp_per_kwh_throughput"]
    import_power_tariff = IMPORT_ECONOMIC["power_tariff_rp_per_kw_per_month"]
    export_power_tariff = EXPORT_ECONOMIC["power_tariff_rp_per_kw_per_month"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_credit = EXPORT_EMISSIONS["export_emissions_credit_kgco2_per_kwh"]

    if import_power_tariff != export_power_tariff:
        raise ValueError("Import and export monthly power tariffs must match.")

    spot_price_series = pd.Series(spot_price, index=results.index, dtype=float)
    month_labels = pd.to_datetime(datetime_series).dt.to_period("M").astype(str)
    first_step_in_month = ~month_labels.duplicated()
    monthly_power_cost_cost = month_labels.map(monthly_peak_cost).astype(float) * import_power_tariff
    monthly_power_cost_emis = month_labels.map(monthly_peak_emis).astype(float) * import_power_tariff
    annual_battery_fixed_cost = battery_capex + battery_annual_opex
    results["cost_opt__monthly_power_tariff_rp"] = 0.0
    results["emissions_opt__monthly_power_tariff_rp"] = 0.0
    results["cost_opt__battery_fixed_cost_rp"] = 0.0
    results["emissions_opt__battery_fixed_cost_rp"] = 0.0
    results.loc[first_step_in_month, "cost_opt__monthly_power_tariff_rp"] = monthly_power_cost_cost[first_step_in_month].values
    results.loc[first_step_in_month, "emissions_opt__monthly_power_tariff_rp"] = monthly_power_cost_emis[first_step_in_month].values
    if len(results) > 0:
        results.loc[results.index[0], "cost_opt__battery_fixed_cost_rp"] = annual_battery_fixed_cost
        results.loc[results.index[0], "emissions_opt__battery_fixed_cost_rp"] = annual_battery_fixed_cost

    results["cost_opt__step_cost_rp"] = (
        results["cost_opt__grid_import_kWh"] * import_price_rp_per_kwh(spot_price_series)
        - results["cost_opt__grid_export_kWh"] * export_price_rp_per_kwh(spot_price_series)
        + battery_degradation_cost
        * (
            results["cost_opt__battery_charge_kWh"]
            + results["cost_opt__battery_discharge_kWh"]
        )
        + results["cost_opt__monthly_power_tariff_rp"]
        + results["cost_opt__battery_fixed_cost_rp"]
    )

    results["emissions_opt__step_cost_rp"] = (
        results["emissions_opt__grid_import_kWh"] * import_price_rp_per_kwh(spot_price_series)
        - results["emissions_opt__grid_export_kWh"] * export_price_rp_per_kwh(spot_price_series)
        + battery_degradation_cost
        * (
            results["emissions_opt__battery_charge_kWh"]
            + results["emissions_opt__battery_discharge_kWh"]
        )
        + results["emissions_opt__monthly_power_tariff_rp"]
        + results["emissions_opt__battery_fixed_cost_rp"]
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
