import pandas as pd

from parameters.battery import BATTERY_ECONOMIC, BATTERY_TECHNICAL
from parameters.grid_import import (
    IMPORT_EMISSIONS,
    annual_grid_use_hours as annual_import_grid_use_hours,
    import_price_rp_per_kwh,
    power_tariff_rp_per_kw_per_month,
)
from parameters.grid_export import (
    EXPORT_EMISSIONS,
    export_price_rp_per_kwh,
)
from parameters.runofriver import RUNOFRIVER_ECONOMIC, RUNOFRIVER_EMISSIONS


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


def build_results_table(
    datetime_series,
    sol_cost,
    sol_emis,
    production,
    spot_price,
    monthly_peak_cost,
    monthly_peak_emis,
):
    results = pd.DataFrame({"DateTime": datetime_series})

    for col in sol_cost.columns:
        results[f"cost_opt__{col}"] = sol_cost[col].values

    for col in sol_emis.columns:
        results[f"emissions_opt__{col}"] = sol_emis[col].values

    battery_capacity_kwh = BATTERY_TECHNICAL["capacity_kwh"]
    battery_capex = BATTERY_ECONOMIC["capex_rp_kwh"] * battery_capacity_kwh
    battery_annual_opex = (
        BATTERY_ECONOMIC["annual_opex_rp_per_kwh_year"] * battery_capacity_kwh
    )
    battery_degradation_cost = BATTERY_ECONOMIC["degradation_cost_rp_per_kwh_throughput"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_emissions = EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
    runofriver_profit_per_kwh = RUNOFRIVER_ECONOMIC["profit_rp_per_kwh"]
    runofriver_emissions_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]

    spot_price_series = pd.Series(spot_price, index=results.index, dtype=float)
    production_series = pd.Series(production, index=results.index, dtype=float)
    annual_grid_use_hours_cost = annual_import_grid_use_hours(
        sol_cost["grid_import_kWh"].sum(),
        sol_cost["grid_export_kWh"].sum(),
    )
    annual_grid_use_hours_emis = annual_import_grid_use_hours(
        sol_emis["grid_import_kWh"].sum(),
        sol_emis["grid_export_kWh"].sum(),
    )
    power_tariff_cost = power_tariff_rp_per_kw_per_month(annual_grid_use_hours_cost)
    power_tariff_emis = power_tariff_rp_per_kw_per_month(annual_grid_use_hours_emis)
    month_labels = pd.to_datetime(datetime_series).dt.to_period("M").astype(str)
    first_step_in_month = ~month_labels.duplicated()
    monthly_power_cost_cost = month_labels.map(monthly_peak_cost).astype(float) * power_tariff_cost
    monthly_power_cost_emis = month_labels.map(monthly_peak_emis).astype(float) * power_tariff_emis
    annual_battery_fixed_cost = battery_capex + battery_annual_opex
    results["cost_opt__monthly_power_tariff_rp"] = 0.0
    results["emissions_opt__monthly_power_tariff_rp"] = 0.0
    results["cost_opt__battery_fixed_cost_rp"] = 0.0
    results["emissions_opt__battery_fixed_cost_rp"] = 0.0
    results["cost_opt__runofriver_profit_rp"] = (
        production_series * runofriver_profit_per_kwh
    )
    results["emissions_opt__runofriver_profit_rp"] = (
        production_series * runofriver_profit_per_kwh
    )
    results.loc[first_step_in_month, "cost_opt__monthly_power_tariff_rp"] = monthly_power_cost_cost[first_step_in_month].values
    results.loc[first_step_in_month, "emissions_opt__monthly_power_tariff_rp"] = monthly_power_cost_emis[first_step_in_month].values
    if len(results) > 0:
        results.loc[results.index[0], "cost_opt__battery_fixed_cost_rp"] = annual_battery_fixed_cost
        results.loc[results.index[0], "emissions_opt__battery_fixed_cost_rp"] = annual_battery_fixed_cost

    results["cost_opt__step_cost_rp"] = (
        results["cost_opt__grid_import_kWh"]
        * import_price_rp_per_kwh(spot_price_series, annual_grid_use_hours_cost)
        - results["cost_opt__grid_export_kWh"]
        * export_price_rp_per_kwh(spot_price_series, annual_grid_use_hours_cost)
        + battery_degradation_cost
        * (
            results["cost_opt__battery_charge_kWh"]
            + results["cost_opt__battery_discharge_kWh"]
        )
        - results["cost_opt__runofriver_profit_rp"]
        + results["cost_opt__monthly_power_tariff_rp"]
        + results["cost_opt__battery_fixed_cost_rp"]
    )

    results["emissions_opt__step_cost_rp"] = (
        results["emissions_opt__grid_import_kWh"]
        * import_price_rp_per_kwh(spot_price_series, annual_grid_use_hours_emis)
        - results["emissions_opt__grid_export_kWh"]
        * export_price_rp_per_kwh(spot_price_series, annual_grid_use_hours_emis)
        + battery_degradation_cost
        * (
            results["emissions_opt__battery_charge_kWh"]
            + results["emissions_opt__battery_discharge_kWh"]
        )
        - results["emissions_opt__runofriver_profit_rp"]
        + results["emissions_opt__monthly_power_tariff_rp"]
        + results["emissions_opt__battery_fixed_cost_rp"]
    )

    results["cost_opt__step_emissions_kgco2"] = (
        results["cost_opt__grid_import_kWh"] * grid_emissions
        + results["cost_opt__grid_export_kWh"] * export_emissions
        + production_series * runofriver_emissions_per_kwh
    )

    results["emissions_opt__step_emissions_kgco2"] = (
        results["emissions_opt__grid_import_kWh"] * grid_emissions
        + results["emissions_opt__grid_export_kWh"] * export_emissions
        + production_series * runofriver_emissions_per_kwh
    )

    return results


def save_results(results, output_path):
    results.to_csv(output_path, index=False)


def print_summary(results, output_path):
    total_cost_costobj = results["cost_opt__step_cost_rp"].sum()
    total_cost_emisobj = results["emissions_opt__step_cost_rp"].sum()
    total_emis_costobj = results["cost_opt__step_emissions_kgco2"].sum()
    total_emis_emisobj = results["emissions_opt__step_emissions_kgco2"].sum()
    net_profit_costobj_chf = -total_cost_costobj / 100.0
    net_profit_emisobj_chf = -total_cost_emisobj / 100.0

    print("Optimization complete.")
    print(f"Rows solved (15-min intervals): {len(results)}")
    print(f"Output file: {output_path}")
    print("")
    print("Annual totals")
    print(f"Cost objective -> net annual profit [CHF]: {net_profit_costobj_chf:,.2f}")
    print(f"Cost objective -> annual emissions burden [kgCO2]: {total_emis_costobj:,.2f}")
    print(f"Emissions objective -> net annual profit [CHF]: {net_profit_emisobj_chf:,.2f}")
    print(f"Emissions objective -> annual emissions burden [kgCO2]: {total_emis_emisobj:,.2f}")
