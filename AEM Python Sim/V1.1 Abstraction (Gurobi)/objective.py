import gurobipy as gp
from gurobipy import GRB

from parameters.battery import BATTERY_ECONOMIC, BATTERY_TECHNICAL
from parameters.grid_import import IMPORT_ECONOMIC, IMPORT_EMISSIONS, import_price_rp_per_kwh
from parameters.grid_export import EXPORT_ECONOMIC, EXPORT_EMISSIONS, export_price_rp_per_kwh


def add_objective(model, vars_dict, spot_price_rp_per_kwh, objective_mode, n):
    grid_import = vars_dict["grid_import"]
    grid_export = vars_dict["grid_export"]
    batt_charge = vars_dict["batt_charge"]
    batt_discharge = vars_dict["batt_discharge"]
    monthly_peak_kw = vars_dict["monthly_peak_kw"]
    unique_month_labels = vars_dict["unique_month_labels"]

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

    if objective_mode == "cost":
        expr = gp.quicksum(
            grid_import[t] * import_price_rp_per_kwh(spot_price_rp_per_kwh[t])
            - grid_export[t] * export_price_rp_per_kwh(spot_price_rp_per_kwh[t])
            + battery_degradation_cost * (batt_charge[t] + batt_discharge[t])
            for t in range(n)
        ) + import_power_tariff * gp.quicksum(
            monthly_peak_kw[month_label] for month_label in unique_month_labels
        ) + battery_capex + battery_annual_opex
    elif objective_mode == "emissions":
        expr = gp.quicksum(
            grid_import[t] * grid_emissions
            - grid_export[t] * export_credit
            for t in range(n)
        )
    else:
        raise ValueError(f"Unknown objective_mode: {objective_mode}")

    model.setObjective(expr, GRB.MINIMIZE)
